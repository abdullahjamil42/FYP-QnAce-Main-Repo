# Q&ACE - Quick Demo Guide for Viva

## 🚀 Quick Start (30 seconds)

```bash
cd /Users/aziqrauf/codes/FYP
./start.sh
```

**Access**:
- Frontend: http://localhost:3000
- Backend: http://localhost:8001
- API Docs: http://localhost:8001/docs

---

## 📋 Demo Flow (5 minutes)

### **1. Show Architecture** (1 min)
```
Frontend (React/Next.js) 
    ↓ HTTP REST API
Backend (FastAPI)
    ↓ Loads 3 Models
Facial + Voice + Text Analysis
    ↓ Fusion Engine
Comprehensive Feedback
```

### **2. Live Demo** (3 min)
1. **Open Frontend** → http://localhost:3000
2. **Navigate** → Practice Sessions
3. **Click** → "New Session"
4. **Record** → Answer a question (30 sec)
5. **Show** → Real-time emotion detection
6. **View** → Report with scores & recommendations

### **3. Technical Highlights** (1 min)
- **3 ML Models**: EfficientNet-B2 (72.72%), Wav2Vec2 (73.37%), BERT
- **Multimodal Fusion**: 50% facial + 40% voice + 10% text
- **REST API**: 5 endpoints, CORS enabled, async processing
- **Real-time**: Frame-by-frame analysis during recording

---

## 🎯 Key Points to Mention

### **Integration**:
✅ Frontend ↔ Backend communication via REST API  
✅ Three ML models integrated seamlessly  
✅ Real-time multimodal analysis  
✅ Comprehensive feedback system  

### **Technology Stack**:
- **Frontend**: Next.js 14, React 18, TypeScript, TailwindCSS
- **Backend**: FastAPI, Python 3.8+, PyTorch
- **Models**: EfficientNet-B2, Wav2Vec2, BERT (Transformers)
- **API**: RESTful, JSON, CORS-enabled

### **Features**:
- Real-time emotion detection
- Multimodal fusion (facial + voice + text)
- Confidence scoring (0-100)
- Personalized recommendations
- Session history & reports

---

## 🔧 If Something Goes Wrong

### **Backend not starting?**
```bash
cd integrated_system
python api/main.py
```

### **Frontend not starting?**
```bash
cd Frontend
npm install
npm run dev
```

### **API not responding?**
```bash
curl http://localhost:8001/health
```

### **Models not loading?**
- Check model files exist in:
  - `interview_emotion_detection/models/`
  - `QnAce_Voice-Model/`
  - `BERT_Model/`

---

## 📊 Expected Outputs

### **Health Check**:
```json
{
  "status": "ok",
  "device": "cpu",
  "models": {
    "facial": true,
    "voice": true,
    "bert": true
  }
}
```

### **Analysis Result**:
```json
{
  "success": true,
  "confidence_score": 75.5,
  "clarity_score": 80.0,
  "engagement_score": 65.0,
  "recommendations": [
    "💡 Great neutral expression!",
    "✅ Good vocal tone!"
  ]
}
```

---

## 💡 Demo Tips

1. **Start with architecture** - Show the big picture first
2. **Live demo** - Actually record and analyze (more impressive)
3. **Show API docs** - http://localhost:8001/docs (shows professionalism)
4. **Mention testing** - "81 tests passing, 54% code coverage"
5. **Future work** - Real-time streaming, mobile app, more models

---

## 🎓 Common Questions & Answers

**Q: Why multimodal instead of single model?**  
A: More robust - if one modality fails, others compensate. Also provides comprehensive feedback.

**Q: Why these specific models?**  
A: State-of-the-art accuracy for emotion detection. EfficientNet-B2 for facial (72.72%), Wav2Vec2 for voice (73.37%).

**Q: How does fusion work?**  
A: Weighted combination - Facial 50%, Voice 40%, Text 10%. Scores normalized and combined.

**Q: Can it scale?**  
A: Yes - FastAPI handles async requests, models can be GPU-accelerated, frontend is server-rendered.

**Q: What's the accuracy?**  
A: Facial 72.72%, Voice 73.37%. Combined multimodal analysis is more reliable than individual models.

---

**Good luck! 🚀**

