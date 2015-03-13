import json
from pprint import pprint
from websocket import create_connection
from prettytable import PrettyTable
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-t", "--token", dest="api_token", help="API Token")
parser.add_option("-s", "--server", dest="server", help="Server address", default="rapid.moixa-data.com")

(options, args) = parser.parse_args()
if not options.api_token:
  parser.error("api token is required")

ws = create_connection("wss://%s:8443/api/ws" % options.server, header=[("Authorization: Token %s" % options.api_token)])

ws.send(json.dumps({'type': 'get-devices', 'msg': {}}))

def powerof(data):
  i = data['current']
  v = data['voltage']
  if i != None and v != None:
    return i*v
  else:
    return float('nan')

def show_devices(devices):
  t = PrettyTable(["Device", "Battery level", "House AC Consumption", "Mains", "Battery", "DC network", "AC PV", "DC PV"])
  for (device_id, device) in devices.items():
    def v(k):
      return "%.0f W" % device.get(k, float('nan'))

    t.add_row([device_id,
               "%.2f Ah (%.0f%%)" % (device.get('battery-amph',float('nan')), device.get('battery-cap',float('nan'))),
               v('accons'), v('mains'), v('battery'), v('network'), v('acpv'), v('dcpv')])

  print(t)

devices = {}

while True:
  payl_str = ws.recv()
  payl = json.loads(payl_str)

  typ = payl['type']
  msg = payl['msg']
  if typ == 'devices':
    for device_id in devices:
      ws.send(json.dumps({'type': 'devices-unlisten', 'msg': {'device-id': device_id}}))
    devices.clear()

    for device_id in map(lambda d: d['id'], msg):
      devices[device_id] = {}
      ws.send(json.dumps({'type': 'devices-listen', 'msg': {'device-id': device_id}}))
  elif typ == 'device-data':
    msg = payl['msg']
    device_id = payl['msg']['id']
    devices[device_id] = {
      'accons'  : powerof(msg['accons']),
      'mains'   : powerof(msg['mains']),
      'network' : powerof(msg['network']),
      'dcpv'    : powerof(msg['dcpv']),
      'acpv'    : powerof(msg['acpv']),
      'battery' : powerof(msg['battery']['power']),
      'battery-amph' : (msg['battery']['amphours'] or float('nan')),
      'battery-cap'  : (msg['battery']['capacity'] or float('nan'))
    }
  elif typ == 'error':
    print('Error: ' + msg)
    break
  else:
    print(payl)

  show_devices(devices)

ws.close()
