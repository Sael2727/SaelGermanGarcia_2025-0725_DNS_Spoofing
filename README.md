# 🌐 DNS Spoofing Attack — Seguridad de Redes

<div align="center">

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python)
![Scapy](https://img.shields.io/badge/Scapy-Latest-green?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Linux-orange?style=for-the-badge&logo=linux)
![License](https://img.shields.io/badge/Uso-Educativo-red?style=for-the-badge)

**Sael Germán García** | Matrícula: `2025-0725`  
Asignatura: Seguridad de Redes | Profesor: Jonathan Rondón  
Instituto Tecnológico de las Américas — ITLA | 2026

</div>

---

## 📋 Descripción del Ataque

El **DNS Spoofing / DNS Poisoning Attack** combina **ARP Poisoning** e interceptación de consultas DNS para falsificar la resolución del dominio `itla.edu.do` y redirigir a la víctima hacia un servidor web local controlado por el atacante. Al posicionarse como intermediario entre la víctima y el gateway mediante ARP falso, el atacante escucha las consultas DNS y responde con una IP falsa (`10.25.10.10`) antes de que llegue la respuesta legítima. La víctima escribe un dominio real y termina en una página web completamente falsa sin notarlo.

> 💡 **Condición de vulnerabilidad:** La víctima y el atacante deben encontrarse en la misma VLAN (VLAN 10). El switch no debe tener Dynamic ARP Inspection habilitado y el DNS de la víctima debe ser externo (8.8.8.8), permitiendo la intercepción.

---

## 🗺️ Topología de Red

### 📊 Parámetros del Ataque

| Parámetro | Valor | Descripción |
|:---------:|:-----:|-------------|
| `IFACE` | `ens3` | Interfaz del atacante conectada a VLAN 10 |
| `TARGET` | `10.25.10.20` | IP de la víctima Ubuntu Server |
| `GATEWAY` | `10.25.10.1` | Gateway de VLAN 10 en R1 |
| `DOMAIN` | `itla.edu.do` | Dominio DNS falsificado |
| `FAKE_IP` | `10.25.10.10` | IP del atacante y servidor web falso |
| DNS original víctima | `8.8.8.8` | DNS real configurado antes del ataque |
| VLAN utilizada | `10` | Segmento compartido por atacante y víctima |

### 📊 Topología de Interfaces

| Dispositivo | Interfaz | Conexión | IP / VLAN | Descripción |
|:-----------:|:--------:|:--------:|:---------:|-------------|
| R1 | e0/1.10 | Subinterfaz VLAN 10 | 10.25.10.1/24 | Gateway de atacante y víctima |
| SW1-CORE | e0/0 | Trunk hacia R1 | VLAN 10 | Transporte VLAN hacia gateway |
| SW1-CORE | e0/2 | Trunk hacia SW2 | VLAN 10 | Enlace entre switches |
| SW1-CORE | e0/3 | Access hacia atacante | VLAN 10 | Puerto del atacante Ubuntu |
| SW2 | e0/0 | Trunk hacia SW1-CORE | VLAN 10 | Enlace de distribución |
| SW2 | e0/1 | Access hacia víctima | VLAN 10 | Puerto Ubuntu Server víctima |
| Atacante | ens3 | Host atacante | 10.25.10.10/24 | Ejecuta ARP Poisoning + DNS Spoof + Web falsa |
| Víctima | eth1 | Host víctima | 10.25.10.20/24 | Realiza consultas DNS y prueba HTTP |

### 📊 Tabla de MACs

| Equipo | Interfaz | IP | MAC |
|:------:|:--------:|:--:|:---:|
| Atacante Ubuntu | ens3 | 10.25.10.10/24 | `50:c0:cc:00:21:00` |
| Víctima Ubuntu Server | eth1 | 10.25.10.20/24 | `50:10:2f:00:33:01` |
| Gateway R1 | e0/1.10 | 10.25.10.1/24 | `aa:bb:cc:00:02:10` |

---

## ⚙️ Requisitos

```bash
# Sistema Operativo
Ubuntu Linux (recomendado) — atacante y víctima

# Dependencias en el atacante
sudo apt update && sudo apt install -y python3-pip python3-scapy
sudo pip3 install scapy

# Privilegios requeridos
sudo / root

# Condiciones de red
# - Atacante y víctima en la misma VLAN 10
# - Gateway R1 con subinterfaz e0/1.10 = 10.25.10.1/24
# - DNS de la víctima configurado como 8.8.8.8 (externo)
# - Switch sin Dynamic ARP Inspection
```

---

## 🚀 Uso

```bash
# En la víctima — estado limpio antes del ataque
sudo ip neigh flush dev eth1
sudo systemctl stop systemd-resolved
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
nslookup itla.edu.do   # Debe mostrar IPs reales de Internet

# En el atacante — ejecutar el script
sudo python3 dns_spoof.py

# En la víctima — verificar con ataque activo
ip neigh show            # Gateway 10.25.10.1 → MAC del atacante
nslookup itla.edu.do     # Debe responder 10.25.10.10
curl http://itla.edu.do  # Muestra la página web falsa
```

---

## 🔬 ¿Cómo funciona?

| Fase | Módulo | Descripción |
|:----:|:------:|-------------|
| 1️⃣ | **IP Forwarding** | Activa `net.ipv4.ip_forward=1` para que el atacante reenvíe tráfico entre víctima y gateway — la víctima mantiene conectividad sin notar el ataque |
| 2️⃣ | **Obtención de MAC** | Usa ARP para obtener las MACs reales de la víctima (`10.25.10.20`) y del gateway (`10.25.10.1`) |
| 3️⃣ | **ARP Poisoning** | Envía respuestas ARP falsas cada 1.5s: a la víctima le dice que el gateway tiene la MAC del atacante; al gateway le dice que la víctima tiene la MAC del atacante |
| 4️⃣ | **Sniffing DNS** | Escucha paquetes UDP puerto 53 con `sniff()` y detecta consultas DNS de la víctima |
| 5️⃣ | **Respuesta DNS falsa** | Cuando detecta `itla.edu.do`, construye y envía un registro A falso apuntando a `10.25.10.10` antes de que llegue la respuesta real |
| 6️⃣ | **Servidor web falso** | Levanta un servidor HTTP en el puerto 80 que sirve una página HTML falsa simulando `itla.edu.do` |
| 7️⃣ | **Limpieza** | Al detener el script (`Ctrl+C`), desactiva IP forwarding e intenta restaurar ARP |

### Estructura del Paquete DNS Falso

| Capa | Campo | Valor |
|:----:|:-----:|-------|
| L2 Ethernet | `src/dst` | MACs intercambiadas (spoofed) |
| L3 IP | `src/dst` | IPs intercambiadas (respuesta del "servidor DNS") |
| L4 UDP | `sport/dport` | `53` / puerto origen de la consulta |
| DNS | `qr=1, aa=1` | Respuesta autoritativa |
| DNS Answer | `DNSRR type=A` | `itla.edu.do → 10.25.10.10` (TTL 300) |

---

## 📊 Evidencias del Ataque

| Evidencia | Resultado Observado |
|:---------:|:-------------------:|
| Estado inicial | `itla.edu.do` resuelve a IPs reales: `104.26.13.23`, `104.26.12.23`, `172.67.69.129` |
| ARP Poisoning | `10.25.10.1` (gateway) aparece asociado a la MAC del atacante `50:c0:cc:00:21:00` |
| DNS Spoofing | `nslookup itla.edu.do` responde `10.25.10.10` |
| Página web falsa | `curl http://itla.edu.do` muestra HTML falso servido por el atacante |
| Logs del atacante | Script muestra `QUERY capturada` → `Respondiendo con -> 10.25.10.10` |

---

## 🛡️ Contramedidas

### 1. Dynamic ARP Inspection + DHCP Snooping en los switches
```cisco
configure terminal
ip dhcp snooping
ip dhcp snooping vlan 10
ip arp inspection vlan 10

! Marcar puertos trunk/uplink como confiables
interface ethernet 0/0
 ip dhcp snooping trust
 ip arp inspection trust
exit
end
write memory
```

### 2. ARP estático en la víctima (medida de endpoint)
```bash
sudo arp -s 10.25.10.1 aa:bb:cc:00:02:10
```

### Resumen de mitigaciones

| Medida | Efecto |
|:------:|--------|
| **Dynamic ARP Inspection** | El switch valida paquetes ARP y bloquea respuestas falsas |
| **DHCP Snooping** | Construye base IP-MAC confiable para que DAI pueda validar ARP |
| **ARP estático** | Fija la MAC real del gateway en la víctima — el atacante no puede sobrescribirla |
| **DNSSEC** | Valida criptográficamente que la respuesta DNS sea auténtica |
| **DNS over HTTPS / TLS** | Cifra las consultas DNS, impidiendo su interceptación y modificación |
| **Segmentación de VLANs** | Separar hosts reduce la superficie de ataque ARP/DNS en la misma VLAN |
| **Monitoreo ARP** | Detectar cambios ARP sospechosos con herramientas de análisis de red |

---

## 📊 Resultados del Laboratorio

| Prueba | Resultado |
|:------:|:---------:|
| Resolución DNS real antes del ataque | ✅ Confirmada — IPs reales de Internet |
| ARP Poisoning: gateway → MAC atacante | ✅ Exitoso |
| DNS Spoofing: `itla.edu.do` → `10.25.10.10` | ✅ Exitoso |
| Víctima accede a la página web falsa | ✅ Exitoso |
| Contramedidas DAI + DHCP Snooping | ✅ Aplicadas |

---

## 📁 Archivos del Repositorio

| Archivo | Descripción |
|:-------:|-------------|
| [`dns_spoof.py`](dns_spoof.py) | Script principal del ataque |
| [`SaelGermanGarcia_2025-0725_DNSSpoofing_P1.pdf`](SaelGermanGarcia_2025-0725_DNSSpoofing_P1.pdf) | Documentación técnica completa |

---

## 🖼️ Capturas de Pantalla

- 📸 [Topología física y lógica utilizada para DNS Spoofing](Capturas%20de%20Pantalla%20DNS%20Spoofing/Topologia%20fisica%20y%20logica%20utilizada%20para%20DNS%20Spoofing.png)
- 📸 [Estado antes del ataque: gateway real y resolución DNS real de itla.edu.do](Capturas%20de%20Pantalla%20DNS%20Spoofing/Figura%202.%20Estado%20antes%20del%20ataque%20gateway%20real%20y%20resolucion%20DNS%20real%20de%20itla.edu.do.png)
- 📸 [Script ejecutándose en el atacante y capturando consultas DNS](Capturas%20de%20Pantalla%20DNS%20Spoofing/Figura%203.%20Script%20ejecutandose%20en%20el%20atacante%20y%20capturando%20consultas%20DNS.png)
- 📸 [Después del ataque: itla.edu.do resuelve hacia 10.25.10.10](Capturas%20de%20Pantalla%20DNS%20Spoofing/Figura%204.%20Despues%20del%20ataque%20itla.edu.do%20resuelve%20hacia%2010.25.10.10.png)
- 📸 [La víctima accede a la página web falsa mediante http://itla.edu.do](Capturas%20de%20Pantalla%20DNS%20Spoofing/Figura%205.%20La%20victima%20accede%20a%20la%20pagina%20web%20falsa%20mediante%20httpitla.edu.do.png)
- 📸 [Activación de DHCP Snooping y Dynamic ARP Inspection en SW1-CORE](Capturas%20de%20Pantalla%20DNS%20Spoofing/Figura%206.%20Activacion%20de%20DHCP%20Snooping%20y%20Dynamic%20ARP%20Inspection%20en%20SW1-CORE.png)

---

## 📎 Recursos

📄 **Documentación Técnica:** [Ver Informe PDF](SaelGermanGarcia_2025-0725_DNSSpoofing_P1.pdf)  
▶️ **Video Demostración:** [Ver en YouTube](https://www.youtube.com/playlist?list=PLV_dKVnYXf6f67jGkXDf8d4dPSeYV39qM)

---

## 📚 Referencias

1. Cisco Systems. *DHCP Snooping and Dynamic ARP Inspection Configuration Guide*. Documentación oficial de Cisco IOS.
2. Scapy Project. *Scapy: Packet crafting and network manipulation framework*. [https://scapy.net/](https://scapy.net/)
3. IETF. *RFC 1035: Domain Names — Implementation and Specification*. Estándar base de DNS.
4. Reconocimiento especial: Troubleshooting, estructura de documentación y apoyo de redacción asistidos con Inteligencia Artificial.

---

<div align="center">

⚠️ **AVISO LEGAL** ⚠️  
*Este script fue desarrollado exclusivamente con fines académicos y educativos.*  
*Su uso en redes sin autorización explícita es ilegal y éticamente inaceptable.*

</div>
