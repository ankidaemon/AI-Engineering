import { PromptEngineeringDemo } from './components/PromptEngineeringDemo';
import './App.css';

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>🎓 Prompt Engineering Techniques Demo</h1>
        <p>A comprehensive learning platform for advanced prompt engineering techniques</p>
      </header>

      <main className="app-main">
        <PromptEngineeringDemo />
      </main>
    </div>
  );
}

export default App;
