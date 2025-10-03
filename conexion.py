from netmiko import ConnectHandler, NetmikoAuthenticationException, NetmikoTimeoutException
import paramiko
import os
from dotenv import load_dotenv
paramiko.transport._DEFAULT_KEX = (
    'diffie-hellman-group1-sha1',
)
load_dotenv()  # Carga el .env
# Dispositivos (cargados desde .env)
router_ips = [os.getenv("ROUTER1_IP"), os.getenv("ROUTER2_IP")]
router_models = [os.getenv("ROUTER1_MODELS"), os.getenv("ROUTER2_MODELS")]
router_users = [os.getenv("ROUTER1_USER"), os.getenv("ROUTER2_USER")]
router_passwords = [os.getenv("ROUTER1_PASS"), os.getenv("ROUTER2_PASS")]

snmp_community = "public"

# Comandos para comprobar SNMP por tipo
snmp_check_commands = {
    "cisco_ios": "show running-config | include snmp-server",
    "juniper": "show configuration | match snmp",
    "mikrotik_routeros": "/snmp print",
    "linux": "ps aux | grep snmpd",
}

# Comandos para habilitar SNMP por tipo
snmp_enable_commands = {
    "cisco_ios": [
        "conf t",
        f"snmp-server community {snmp_community} RO",
        "end"
    ],
    "juniper": [
        "configure",
        f"set snmp community {snmp_community} authorization read-only",
        "commit and-quit"
    ],
    "mikrotik_routeros": [
        "/snmp set enabled=yes",
        f"/snmp community set 0 name={snmp_community}"
    ],
    "linux": [
        "sudo systemctl start snmpd",
        f"sudo sed -i 's/^com2sec.*/com2sec readonly default {snmp_community}/' /etc/snmp/snmpd.conf",
        "sudo systemctl restart snmpd"
    ]
}

#Conectar al dispositivo
def conectar_dispositivo(ip, device_type, user, passwd):
    device = {
        "device_type": device_type,
        "host": ip,
        "username": user,
        "password": passwd,
        "secret": passwd
    }
    return ConnectHandler(**device)

#Verificar si snmp está activo
def verificar_snmp(net_connect, device_type, ip):
    check_cmd = snmp_check_commands.get(device_type)
    if not check_cmd:
        print(f"⚠️ No hay comando de verificación SNMP definido para {device_type}")
        return None

    output = net_connect.send_command(check_cmd)

    if device_type == "mikrotik_routeros":
        return "enabled: yes" in output
    else:
        return snmp_community in output



# Activar snmp si es necesario

def activar_snmp(net_connect, device_type, ip):
    config_cmds = snmp_enable_commands.get(device_type)
    if not config_cmds:
        print(f"⚠️ No hay comandos para activar SNMP en {device_type}")
        return

    if device_type == "mikrotik_routeros":
        for cmd in config_cmds:
            net_connect.send_command(cmd)
    else:
        net_connect.send_config_set(config_cmds, exit_config_mode=False)
    
    print(f"✅ SNMP habilitado correctamente en {ip}")

# Bucle principal
def main():
    for ip, device_type, user, passwd in zip(router_ips, router_models, router_users, router_passwords):
        print(f"\n🔌 Conectando a {ip} ({device_type})...")

        try:
            net_connect = conectar_dispositivo(ip, device_type, user, passwd)

            snmp_activo = verificar_snmp(net_connect, device_type, ip)
            if snmp_activo is None:
                net_connect.disconnect()
                continue
            elif snmp_activo:
                print(f"✅ SNMP ya está activado en {ip}")
            else:
                print(f"⚙️ SNMP no está activo en {ip}, activando...")
                activar_snmp(net_connect, device_type, ip)

            net_connect.disconnect()
            print(f"🔒 Conexión cerrada con {ip}")

        except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
            print(f"❌ Error de conexión en {ip}: {e}")
        except Exception as e:
            print(f"⚠️ Error general en {ip}: {e}")

#Ejecutar el script
if __name__ == "__main__":
    main()


