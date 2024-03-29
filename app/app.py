import unicodedata
from collections import OrderedDict

from flask import Flask
from flask import render_template, request, stream_with_context, Response, send_file
from werkzeug.urls import url_quote

from backlash import *

app = Flask(__name__)
# app.config['TEMPLATES_AUTO_RELOAD'] = True


@app.route('/')
def hello_world():
    return render_template('index.html')


@app.route('/compensate', methods=['POST'])
def compensate():
    file = request.files['gcode']
    fname = file.filename.split('.')[0]
    newfname = f'{fname}_nolash.gcode'
    INPUT = file.stream

    CORRECTION = request.form['correction']
    X_DISTANCE_MM = request.form['x_dist']
    Y_DISTANCE_MM = request.form['y_dist']
    Z_DISTANCE_MM = request.form['z_dist']
    # X_OFFSET = request.form['x_offset']
    # Y_OFFSET = request.form['y_offset']
    Z_OFFSET = request.form['z_offset']

    axes = {
        'X': Axis(lash=X_DISTANCE_MM, correction=CORRECTION),
        'Y': Axis(lash=Y_DISTANCE_MM, correction=CORRECTION),
        'Z': Axis(lash=Z_DISTANCE_MM, correction=CORRECTION, offset=Z_OFFSET),
    }

    gcodes = Gcode.parse((l.decode() for l in INPUT))
    gen = ((str(x)+"\n").encode('utf8') for x in backlash_compensate(axes, gcodes))

    resp = Response(stream_with_context(gen),
                    mimetype="text/plain",
                    content_type='application/octet-stream'
                    )
    filenames = OrderedDict()
    try:
        filename = newfname.encode('latin-1')
    except UnicodeEncodeError:
        filenames['filename'] = unicodedata.normalize('NFKD', newfname).encode('latin-1', 'ignore')
        filenames['filename*'] = "UTF-8''{}".format(url_quote(newfname))
    else:
        filenames['filename'] = filename

    resp.headers.add("Content-Disposition", "attachment", **filenames)
    return resp


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=80)
