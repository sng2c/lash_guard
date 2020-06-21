from backlash import *

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    import argparse

    parser = argparse.ArgumentParser(description='Backlash Compensator',
                                     usage='%(prog)s -x 0.6 -y 0.6 sample.gcode -o out.gcode')
    parser.add_argument('-a', '--auto', help='AUTO compensation', action='store_true')
    parser.add_argument('-x', '--x-dist', help='X_DISTANCE_MM', type=float, default=0.0)
    parser.add_argument('--x-offset', help='X_OFFSET_MM', type=float, default=0.0)
    parser.add_argument('-y', '--y-dist', help='Y_DISTANCE_MM', type=float, default=0.0)
    parser.add_argument('--y-offset', help='Y_OFFSET_MM', type=float, default=0.0)
    parser.add_argument('-z', '--z-dist', help='Z_DISTANCE_MM', type=float, default=0.0)
    parser.add_argument('--z-offset', help='Z_OFFSET_MM', type=float, default=0.0)
    parser.add_argument('-c', '--correction', help='CORRECTION', type=float, default=1.0)
    parser.add_argument('input', help='INPUT G-code', type=str)
    parser.add_argument('-o', '--output', type=str, default='out.gcode')
    args = parser.parse_args()

    INPUT = args.input
    OUTPUT = args.output

    CORRECTION = args.correction
    X_DISTANCE_MM = args.x_dist
    Y_DISTANCE_MM = args.y_dist
    Z_DISTANCE_MM = args.z_dist
    X_OFFSET = args.x_offset
    Y_OFFSET = args.y_offset
    Z_OFFSET = args.z_offset
    ENABLE_AUTO = args.auto

    axes = {
        'X': Axis(lash=X_DISTANCE_MM, offset=X_OFFSET, correction=CORRECTION),
        'Y': Axis(lash=Y_DISTANCE_MM, offset=Y_OFFSET, correction=CORRECTION),
        'Z': Axis(lash=Z_DISTANCE_MM, offset=Z_OFFSET, correction=CORRECTION),
    }

    print_axes(axes)
    with open(INPUT) as gcode_data:
        with open(OUTPUT, 'w') as output:
            gcodes = Gcode.parse(gcode_data)

            if ENABLE_AUTO:
                axes2 = {
                    'X': Axis(),
                    'Y': Axis(),
                    'Z': Axis(),
                }
                mod = make_one_direction(axes2, gcodes)
                mod2 = backlash_compensate_auto(axes, mod)
                for gcode in mod:
                    output.write(str(gcode)+"\n")

            else:
                for gcode in backlash_compensate(axes, gcodes):
                    output.write(str(gcode)+"\n")

