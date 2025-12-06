import { useState, useEffect } from 'react';

interface Technique {
  name: string;
  description: string;
  useCase: string;
}

interface ExampleQuery {
  id: number;
  query: string;
  description: string;
}

interface TestResult {
  success: boolean;
  technique: string;
  query: string;
  persona: any;
  results: any;
  educationalNotes: {
    technique: string;
    description: string;
    useCase: string;
    tips: string[];
    prompt: string;
  };
}

export function PromptEngineeringDemo() {
  const [techniques, setTechniques] = useState<Record<string, Technique>>({});
  const [exampleQueries, setExampleQueries] = useState<ExampleQuery[]>([]);
  const [selectedQuery, setSelectedQuery] = useState('');
  const [selectedTechnique, setSelectedTechnique] = useState('all');
  const [persona, setPersona] = useState({
    tone: 'neutral',
    formality: 'neutral',
    verbosity: 'standard'
  });
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [customQuery, setCustomQuery] = useState('');

  useEffect(() => {
    // Load techniques and example queries
    const loadData = async () => {
      try {
        const [techniquesRes, queriesRes] = await Promise.all([
          fetch('/v1/demo/techniques').then(res => res.json()),
          fetch('/v1/demo/example-queries').then(res => res.json())
        ]);
        
        if (techniquesRes.success) {
          setTechniques(techniquesRes.techniques);
        }
        
        if (queriesRes.success) {
          setExampleQueries(queriesRes.queries);
          if (queriesRes.queries.length > 0) {
            setSelectedQuery(queriesRes.queries[0].query);
          }
        }
      } catch (error) {
        console.error('Failed to load demo data:', error);
      }
    };

    loadData();
  }, []);

  const handleTestTechnique = async () => {
    const query = customQuery || selectedQuery;
    if (!query.trim()) return;

    setLoading(true);
    try {
      const response = await fetch('/v1/demo/test-techniques', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          technique: selectedTechnique,
          persona
        }),
      });

      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      console.error('Failed to test technique:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderResults = () => {
    if (!testResult) return null;

    const { results, educationalNotes } = testResult;

    return (
      <div className="demo-results">
        <h3>Test Results</h3>
        <div className="educational-info">
          <h4>Technique: {educationalNotes.technique}</h4>
          <p><strong>Description:</strong> {educationalNotes.description}</p>
          <p><strong>Use Case:</strong> {educationalNotes.useCase}</p>
          <p><strong>Prompt to LLM:</strong> {educationalNotes.prompt}</p>
          <div>
            <strong>Tips:</strong>
            <ul>
              {educationalNotes.tips.map((tip, index) => (
                <li key={index}>{tip}</li>
              ))}
            </ul>
          </div>
        </div>
        
        <div className="technique-results">
          <h4>Generated Responses:</h4>
          {/* {Object.entries(results).map(([technique, response]) => ( */}
            <div className="result-item">
              {/* <h5>{technique.charAt(0).toUpperCase() + technique.slice(1)}:</h5> */}
              <div className="response-text">
                {results}
              </div>
            </div>
          {/* ))} */}
        </div>
      </div>
    );
  };

  return (
    <div className="prompt-engineering-demo">
      <div className="demo-header">
        <h2>🎓 Prompt Engineering Techniques Demo</h2>
        <p>
          This interactive demo allows you to test different prompt engineering techniques 
          and see how they produce different responses to the same query.
        </p>
      </div>

      <div className="demo-controls">
        <div className="control-section">
          <h3>1. Select a Query</h3>
          <div className="query-selection">
            <div className="example-queries">
              <label>Example Queries:</label>
              <select 
                value={selectedQuery} 
                onChange={(e) => setSelectedQuery(e.target.value)}
              >
                {exampleQueries.map((query) => (
                  <option key={query.id} value={query.query}>
                    {query.query}
                  </option>
                ))}
              </select>
              <small>{exampleQueries.find(q => q.query === selectedQuery)?.description}</small>
            </div>
            
            <div className="custom-query">
              <label>Or enter your own query:</label>
              <textarea
                value={customQuery}
                onChange={(e) => setCustomQuery(e.target.value)}
                placeholder="Enter your custom query here..."
                rows={3}
              />
            </div>
          </div>
        </div>

        <div className="control-section">
          <h3>2. Select a Technique</h3>
          <div className="technique-selection">
            <select 
              value={selectedTechnique} 
              onChange={(e) => setSelectedTechnique(e.target.value)}
            >
              {Object.entries(techniques).map(([key, technique]) => (
                <option key={key} value={key}>
                  {technique.name}
                </option>
              ))}
            </select>
            
            {techniques[selectedTechnique] && (
              <div className="technique-info">
                <p><strong>Description:</strong> {techniques[selectedTechnique].description}</p>
                <p><strong>Use Case:</strong> {techniques[selectedTechnique].useCase}</p>
              </div>
            )}
          </div>
        </div>

        <div className="control-section">
          <h3>3. Configure Persona (Optional)</h3>
          <div className="persona-config">
            <div className="persona-control">
              <label>Tone:</label>
              <select 
                value={persona.tone} 
                onChange={(e) => setPersona(prev => ({ ...prev, tone: e.target.value }))}
              >
                <option value="empathetic">Empathetic</option>
                <option value="urgent">Urgent</option>
                <option value="neutral">Neutral</option>
                <option value="friendly">Friendly</option>
                <option value="professional">Professional</option>
              </select>
            </div>
            
            <div className="persona-control">
              <label>Formality:</label>
              <select 
                value={persona.formality} 
                onChange={(e) => setPersona(prev => ({ ...prev, formality: e.target.value }))}
              >
                <option value="informal">Informal</option>
                <option value="neutral">Neutral</option>
                <option value="formal">Formal</option>
              </select>
            </div>
            
            <div className="persona-control">
              <label>Verbosity:</label>
              <select 
                value={persona.verbosity} 
                onChange={(e) => setPersona(prev => ({ ...prev, verbosity: e.target.value }))}
              >
                <option value="concise">Concise</option>
                <option value="standard">Standard</option>
                <option value="elaborate">Elaborate</option>
              </select>
            </div>
          </div>
        </div>

        <div className="control-section">
          <h3>4. Test the Technique</h3>
          <button 
            className="test-button"
            onClick={handleTestTechnique}
            disabled={loading || (!selectedQuery && !customQuery.trim())}
          >
            {loading ? 'Testing...' : 'Test Technique'}
          </button>
        </div>
      </div>

      {renderResults()}

      <div className="demo-footer">
        <h3>💡 Learning Tips</h3>
        <ul>
          <li>Try the same query with different techniques to see how responses vary</li>
          <li>Experiment with different personas to understand their impact</li>
          <li>Compare the "All Techniques" option to see all approaches at once</li>
          <li>Use the educational notes to understand when to use each technique</li>
          <li>Practice with your own queries to develop intuition</li>
        </ul>
      </div>
    </div>
  );
}
