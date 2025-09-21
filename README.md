# SOC Prediction and Battery Management

Bu proje, **elektrikli araç batarya yönetimi ve SOC (State of Charge) tahmini** için geliştirilmiş bir uygulamadır. Projede iki ana bölüm bulunur: frontend (React) ve backend (Python ML). Docker kullanılarak çalıştırılır.

## 📁 Proje Yapısı

```
SOC-Prediction-And-Battery-Management/
├─ frontend/        # React kullanıcı arayüzü
├─ backend/         # Python ML ve batarya yönetimi
├─ docker-compose.yml
├─ Dockerfile (frontend veya backend)
└─ README.md
```

## 🐳 Docker ile Kurulum ve Çalıştırma

1. Docker ve Docker Compose kurulu olduğundan emin olun.

2. Proje kök dizininde terminali açın:

```bash
cd SOC-Prediction-And-Battery-Management
```

3. Docker Compose ile hem frontend hem backend’i tek komutla başlatın:

```bash
docker-compose up --build -d  
```

* `--build` flag’i Docker imajlarını yeniden oluşturur.

4. Çalışan servisler:

* Frontend: `http://localhost:3000`
* Backend API: Docker Compose ile expose edilen port üzerinden

5. Kapatmak için:

```bash
docker-compose down
```

## 🚀 Kullanım

* Tarayıcıda `http://localhost:3000` açarak uygulamayı kullanabilirsiniz.
* Backend, batarya verilerini işler ve SOC tahminlerini frontend’e gönderir.

## 🛠 Teknolojiler

* **Frontend**: React, JavaScript, HTML, CSS
* **Backend**: Python, NumPy, Pandas, TensorFlow / scikit-learn
* **Containerization**: Docker, Docker Compose


