import React, { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

export default function App() {
  const [socData, setSocData] = useState({});        
  const [forecastData, setForecastData] = useState({}); 
  const [batteries, setBatteries] = useState([]);
  const [selectedBattery, setSelectedBattery] = useState("");
  const [selectedModel, setSelectedModel] = useState("LinearRegression");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);


  useEffect(() => {
    const fetchBatteries = async () => {
      try {
        const res = await fetch(`${API_URL}/list_batteries/`);
        const data = await res.json();

        setBatteries(data.batteries);
        if (data.batteries.length > 0 && !selectedBattery) {
          setSelectedBattery(data.batteries[0]);
        }

        const newSocData = { ...socData };
        const newForecastData = { ...forecastData };
        data.batteries.forEach(b => {
          if (!(b in newSocData)) newSocData[b] = [];
          if (!(b in newForecastData)) newForecastData[b] = [];
        });
        setSocData(newSocData);
        setForecastData(newForecastData);
      } catch (err) {
        console.error("Batarya listesi çekilemedi:", err);
      }
    };
    fetchBatteries();
  }, []);

  
  const fetchAllSOC = async (battery, model) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/predict_all/${battery}?model_name=${model}`);
      const data = await res.json();

      setSocData(prev => ({ ...prev, [battery]: data.predicted || [] }));
      setForecastData(prev => ({ ...prev, [battery]: data.forecast || [] }));

    } catch (err) {
      console.error("API hatası:", err);
    }
    setLoading(false);
  };

  const handlePredict = () => {
    if (selectedBattery) fetchAllSOC(selectedBattery, selectedModel);
  };

 
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_URL}/upload_battery/`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      const newBatteryName = file.name.split(".")[0];

      setSocData(prev => ({ ...prev, [newBatteryName]: [] }));
      setForecastData(prev => ({ ...prev, [newBatteryName]: [] }));
      setBatteries(prev => [...prev, newBatteryName]);
      setSelectedBattery(newBatteryName);

      alert(data.message);
    } catch (err) {
      console.error("Upload hatası:", err);
      alert("Batarya yüklenirken hata oluştu.");
    }
    setUploading(false);
  };

  const selectedSoc = socData[selectedBattery] || [];
  const selectedForecast = forecastData[selectedBattery] || [];


  const totalCycles = selectedSoc.length + selectedForecast.length;
  const chartData = Array.from({ length: totalCycles }, (_, index) => {
    const socValue = index < selectedSoc.length ? selectedSoc[index] : null;
    const forecastValue = index >= selectedSoc.length ? selectedForecast[index - selectedSoc.length] : null;

    return {
      name: index + 1,
      SOC: socValue,
      Forecast: forecastValue
    };
  });

  return (
    <div className="container">
      <h1>Elektrikli Araç SOC Tahmini ve Batarya
Yönetimi</h1>

      <div className="selectors">
        <label>
          Batarya:
          <select value={selectedBattery} onChange={(e) => setSelectedBattery(e.target.value)}>
            {batteries.map(bat => (
              <option key={bat} value={bat}>{bat}</option>
            ))}
          </select>
        </label>

        <label>
          Model:
          <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
            <option value="LinearRegression">Linear Regression</option>
            <option value="DecisionTree">Decision Tree</option>
            <option value="RandomForest">Random Forest</option>
            <option value="XGBoost">XGBoost</option>
            <option value="LSTM">LSTM</option>
          </select>
        </label>

        <button
          onClick={handlePredict}
          className="btn"
          disabled={loading}
        >
          {loading && <span className="spinner"></span>}
          {loading ? "Predicting..." : "Predict"}
        </button>

        <label className="upload-btn">
          {uploading ? "Yükleniyor..." : "Yeni Batarya Yükle"}
          <input type="file" accept=".mat" onChange={handleUpload} disabled={uploading} />
        </label>
      </div>

      <div className="chart-card">
        <h2>Grafik</h2>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData} margin={{ top: 20, right: 50, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" label={{ value: "Cycle", position: "insideBottomRight", offset: -5 }} />
            <YAxis domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} label={{ value: "SOC", angle: -90, position: "insideLeft" }} />
            <Tooltip />
            <Legend verticalAlign="top" height={36} />
            <Line type="monotone" dataKey="SOC" stroke="#4caf50" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="Forecast" stroke="#ff9800" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="soc-list-card">
        <h2>SOC Tahminleri</h2>
        <div className="soc-list">
          {selectedSoc.map((v, i) => (
            <div key={i}>
              Cycle {i + 1}: {v.toFixed(3)}
              {selectedForecast[i] !== undefined && (
                <span> | Forecast: {selectedForecast[i].toFixed(3)}</span>
              )}
            </div>
          ))}
        </div>
        {selectedSoc.length > 0 && (
          <div className="average-soc">
            Ortalama SOC: {(selectedSoc.reduce((a, b) => a + b, 0) / selectedSoc.length).toFixed(3)}
          </div>
        )}
      </div>
    </div>
  );
}
