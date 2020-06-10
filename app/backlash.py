import logging
import decimal


class Gcode:
    @classmethod
    def parse(cls, lines):
        for line in lines:
            yield cls.fromStr(line)

    @classmethod
    def _tokenize_gcode(cls, line):
        chunks = line.split(';', 1)
        comment = ''
        if len(chunks) == 2:
            comment = ';' + chunks[1].rstrip()
        if len(chunks[0]) == 0:
            return None, None
        return chunks[0].rstrip().split(), comment

    @classmethod
    def _parse_param(cls, token):
        return token[0], decimal.Decimal(token[1:])

    @classmethod
    def fromStr(cls, cmdstr):
        cmdstr = cmdstr.strip()
        tokens, comment = cls._tokenize_gcode(cmdstr)
        cmd = tokens[0] if tokens is not None else None
        if cmd in ['G0', 'G1', 'G28', 'M425']:
            params = dict(cls._parse_param(token) for token in tokens[1:]) if tokens is not None else None
        else:
            cmd = None
            params = None
        return cls(cmd, params, comment, cmdstr)

    def __init__(self, cmd, params, comment='', rawdata=''):
        self.cmd = cmd
        self.params = params
        self.rawdata = rawdata
        self.comment = comment

    def __repr__(self):
        if self.cmd is not None:
            return "Gcode('{}', '{}', '{}', '{}')".format(self.cmd, self.params, self.comment, self.rawdata)
        else:
            return self.rawdata

    def __str__(self):
        return ' '.join([self.cmd, *[k + str(round(float(self.params[k]), 4)).rstrip('0').rstrip('.') for k in
                                     self.params], self.comment]) if self.cmd is not None else self.rawdata


class Axis:
    def __init__(self, lash=0.0, correction=1.0, offset=0.0, pos=0.0, direction=0, err=0.0):
        self.pos = decimal.Decimal(pos)
        self.lash = decimal.Decimal(lash)
        self.error = decimal.Decimal(err)
        self.correction = decimal.Decimal(correction)
        self.direction = direction
        self.offset = decimal.Decimal(offset)
        self.stack = []

    def push(self, pos):
        self.stack.append(pos)

    def pop(self, pos):
        return self.stack.pop()

    def calc_direction(self, newpos):
        delta = newpos - self.pos
        if delta > 0:
            newdir = 1
        elif delta < 0:
            newdir = -1
        else:
            newdir = self.direction
        return newdir

    def reset(self):
        self.direction = 0
        self.pos = 0

    def move_to(self, newpos):
        last_calc_pos = self.calc_pos()
        newdir = self.calc_direction(newpos)

        preceding_pos = None
        if newdir != self.direction:
            self.direction = newdir

            preceding_err = self.calc_err() * self.direction
            if preceding_err != 0:
                preceding_pos = last_calc_pos + preceding_err

        self.pos = newpos

        return preceding_pos

    def calc_err(self):
        return self.lash * self.correction

    def calc_pos(self):
        # when forward direction, append error
        err_factor = 1 if self.direction > 0 else 0
        return self.pos + self.offset + (self.calc_err() * err_factor)

    def __repr__(self):
        return "Axis(lash={}, correction={}, offset={}, pos={}, direction={})".format(self.lash, self.correction,
                                                                                      self.offset, self.pos,
                                                                                      self.direction)

    def __str__(self):
        return self.__repr__()


def print_axes(axes):
    for sign in axes:
        print("{}: {}".format(sign, axes[sign]))


def backlash_compensate(axes, gcodes):
    for gcode in gcodes:
        if gcode.cmd in ['G0', 'G1']:
            for sign in gcode.params:
                if sign in axes:
                    preceding_pos = axes[sign].move_to(gcode.params[sign])
                    if preceding_pos is not None:
                        yield Gcode(
                            'G1', {sign: preceding_pos},
                            ';fix {}'.format('fwd' if axes[sign].direction == 1 else 'bwd'))
                    gcode.params[sign] = axes[sign].calc_pos()

        if gcode.cmd in ['G28']:
            axes['X'].reset()
            axes['Y'].reset()

        if gcode.cmd in ['M425']:
            if 'F' in gcode.params:
                for sign in axes:
                    axes[sign].correction = gcode.params['F']

            for sign in axes:
                if sign in gcode.params:
                    axes[sign].lash = gcode.params[sign]

            print("Applied ", gcode)
            print_axes(axes)

            # make comment M425
            gcode.cmd = None
            gcode.rawdata = ';Backlash Compensation by ' + gcode.rawdata

        yield gcode


def backlash_compensate_auto(axes, gcodes):
    for gcode in gcodes:
        if gcode.cmd in ['G0', 'G1']:
            gomoreGcode = Gcode('G1', {}, ';pass')
            for sign in gcode.params:
                if sign in axes:
                    lastdir = axes[sign].direction
                    lastpos = axes[sign].pos
                    newpos = gcode.params[sign]
                    newdir = axes[sign].calc_direction(newpos)
                    if newdir == 1 and newdir != lastdir:
                        # 지나갔다가
                        calc_pos = newpos + axes[sign].calc_err() * newdir
                        gomoreGcode.params[sign] = calc_pos
                        axes[sign].move_to(calc_pos)
                    axes[sign].move_to(newpos)

            if bool(gomoreGcode.params):
                yield gomoreGcode

        if gcode.cmd in ['G28']:
            axes['X'].reset()
            axes['Y'].reset()

        elif gcode.cmd in ['M425']:
            gcode.cmd = None
            gcode.rawdata = ';Omitting ' + gcode.rawdata

        yield gcode


'''
위치가 같을때 리버스 잡히는거.
G1 Y10 ;rev
G1 X0 Y10 E10 
G1 Y10 ;ret
'''


def make_one_direction(axes, gcodes):
    for gcode in gcodes:
        if gcode.cmd in ['G0', 'G1']:
            hasE = 'E' in gcode.params
            if hasE:  # 그릴때만 체크
                reverseGcode = Gcode('G1', {}, ';rev')
                resetGcode = Gcode('G1', {}, ';ret')
                for sign in gcode.params:
                    if sign in axes:
                        lastdir = axes[sign].direction
                        lastpos = axes[sign].pos
                        newpos = gcode.params[sign]
                        newdir = axes[sign].calc_direction(newpos)

                        if newdir == 1:
                            # 거꾸로
                            resetGcode.params[sign] = newpos
                            reverseGcode.params[sign] = newpos
                            gcode.params[sign] = lastpos

                        axes[sign].move_to(newpos)

                if bool(reverseGcode.params):
                    yield reverseGcode

                yield gcode

                if bool(resetGcode.params):
                    yield resetGcode

                continue

        if gcode.cmd in ['G28']:
            axes['X'].reset()
            axes['Y'].reset()

        elif gcode.cmd in ['M425']:
            gcode.cmd = None
            gcode.rawdata = ';Omitting ' + gcode.rawdata

        yield gcode
