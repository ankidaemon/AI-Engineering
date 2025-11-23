# 🎓 Prompt Engineering Techniques Demo

A comprehensive learning platform for understanding and practicing advanced prompt engineering techniques in real-world applications.

## 🎯 Overview

This project demonstrates **8 key prompt engineering techniques** with clear examples and interactive testing:

1. **Few-Shot Learning** - Teaching by example
2. **Chain-of-Thought (CoT)** - Step-by-step reasoning  
3. **ReAct** - Reasoning + Acting framework
4. **Self-Consistency** - Multiple response generation
5. **Self-Critique** - Self-evaluation
6. **Reflective Prompting** - Deep reflection before responding
7. **Tree-of-Thoughts (ToT)** - Multiple reasoning paths
8. **Prompt Chaining** - Sequential task breakdown

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Build the application**:
   ```bash
   npm run build          # Build backend
   npm run frontend:build # Build frontend
   ```

3. **Run the application**:
   ```bash
   npm start              # Production mode
   # OR
   npm run dev:full       # Development mode (backend + frontend)
   ```

4. **Access the application**:
   - Demo Interface: http://localhost:3000
   - API Health: http://localhost:3000/health

## 📚 Educational Features

### Interactive Demo Interface
- **Test different techniques** on the same query
- **Compare responses** side by side
- **Configure personas** to see their impact
- **Educational notes** and best practices for each technique

### API Endpoints for Learning
- `POST /v1/demo/test-techniques` — Test different prompt engineering techniques
- `GET /v1/demo/example-queries` — Get example queries for testing
- `GET /v1/demo/techniques` — Get information about available techniques

### Comprehensive Documentation
- **PROMPT_ENGINEERING_GUIDE.md** - Detailed explanations of each technique
- **IMPLEMENTATION_SUMMARY.md** - Technical implementation details
- **Code comments** throughout the codebase explaining each approach

## 🏗️ Project Structure

```
├── src/
│   ├── services/
│   │   ├── generator.ts                    # Main generator with all techniques
│   │   └── advancedPromptEngineering.ts    # Individual technique implementations
│   └── routes/
│       └── demo.ts                         # Demo API endpoints
├── frontend/
│   └── src/
│       ├── components/
│       │   └── PromptEngineeringDemo.tsx   # Interactive demo interface
│       ├── App.tsx                         # Main app component
│       └── App.css                         # Demo-specific styles
├── PROMPT_ENGINEERING_GUIDE.md             # Educational guide
└── IMPLEMENTATION_SUMMARY.md               # Technical summary
```

## 🎓 Learning Objectives

After using this demo, you will be able to:

1. **Understand** when to use each prompt engineering technique
2. **Implement** each technique in your own projects
3. **Compare** different approaches on the same problem
4. **Evaluate** the effectiveness of various techniques
5. **Design** prompt engineering solutions for real-world scenarios

## 🔧 Configuration

- **Environment Variables**: Create `.env` file with:
  - `PORT` (optional, defaults to 3000)
  - `OPENAI_API_KEY` (optional, uses fallback responses if not set)

## 📖 Usage Examples

### Testing via API
```bash
# Test a specific technique
curl -X POST http://localhost:3000/v1/demo/test-techniques \
  -H "Content-Type: application/json" \
  -d '{"query": "I need help with my account", "technique": "fewShot"}'

# Get example queries
curl http://localhost:3000/v1/demo/example-queries

# Get technique information
curl http://localhost:3000/v1/demo/techniques
```

### Interactive Learning
1. Open http://localhost:3000 in your browser
2. Select from pre-built example queries or enter your own
3. Choose different prompt engineering techniques
4. Configure persona settings (tone, formality, verbosity)
5. Compare responses and learn from educational notes

## 🎯 Educational Value

This project serves as a **comprehensive learning resource** for:

- **Students** learning prompt engineering
- **Developers** implementing AI features
- **Researchers** studying prompt techniques
- **Practitioners** improving their AI applications

Each technique is implemented with:
- **Clear examples** and explanations
- **Real-world scenarios** (customer service context)
- **Interactive testing** capabilities
- **Educational metadata** and best practices

## 📚 Further Reading

- [PROMPT_ENGINEERING_GUIDE.md](./PROMPT_ENGINEERING_GUIDE.md) - Detailed technique explanations
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Technical implementation details

---

**Built for educational purposes** - A comprehensive platform for learning advanced prompt engineering techniques through practical examples and interactive experimentation.
