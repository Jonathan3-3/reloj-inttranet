from zk import ZK

zk = ZK(
    '10.10.0.3',
    port=4370,
    timeout=10,
    password=0,
    force_udp=False,
    ommit_ping=True,
)

try:
    conn = zk.connect()
    print('Conectado correctamente')
    print(conn.get_device_name())
    print(conn.get_firmware_version())
    conn.disconnect()
except Exception as e:
    print(type(e).__name__)
    print(e)
