# **Dokumentasi MQTT untuk Showroom Mobil Sport dengan Python**

## Kelompok B

| Nama                     | NRP        |
| ------------------------ | ---------- |
| Hazwan Adhikara Nasution | 5027231017 |
| Rafael Gunawan           | 5027231019 |
| Rama Owarianto           | 5027231049 |

## Deskripsi Project

> Implementasi berbagai fitur MQTT dan MQTT S untuk sebuah aplikasi showroom mobil sport. Fitur yang di‐cover meliputi koneksi MQTT S, autentikasi, QoS 0/1/2, pesan retained, Last Will & Testament (LWT), Message Expiry (broker‐level dan application‐level), Request–Response (MQTT 5.0), Flow Control (rate limiting), serta mekanisme Ping/Pong untuk keep‐alive.

## Struktur File

- **`publisher.py`** : Skrip yang berfungsi sebagai “publisher” — mengirim data inventaris, status, sensor, price update, LWT, expiry, request–response, flow control.

- **`subscriber.py`** : Skrip yang berfungsi sebagai “subscriber” — mendengarkan berbagai topik, mem‐proses pesan, mengirim balasan untuk request–response, dan menampilkan LWT atau expiry.

- **test/** :

  - **`request_response.py`** : Menguji fitur Request–Response (MQTT 5.0).
  - **`expiry.py`** : Menguji Message Expiry (MQTT 5.0 broker‐level + application‐level).
  - **`flow_control.py`** : Menguji Flow Control (rate limit).

## How to run it?

1. Install Dependensi

```bash
pip install paho-mqtt
```

2. Jalankan Subscriber

```bash
python3 subscriber.py
```

> Subscriber sekarang “listening” ke semua topik yang di‐subscribe (inventory, sensor, status, price, expiry, request, flow, lwt).

3. Jalankan Publisher

```bash
python3 publisher.py
```

> Melakukan beberapa contoh publish (inventory, status, sensor, price, expiry, request, flow), lalu disconnect normal.

4. Uji LWT (Last Will)

> Setelah `publisher.py` sedang berjalan, force‐kill (misal `kill -9 PID`) sehingga publisher tidak melakukan disconnect clean. Subscriber akan mencetak LWT.

5. Jalankan Skrip Pengujian

- Request–Response:

```
python3 test_request_response.py
```

- Expiry:

```
python3 test_expiry.py
```

- Flow Control:

```
python3 test_flow_control.py
```
