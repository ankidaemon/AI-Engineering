import OpenAI from 'openai';

// Define Persona type locally since we removed the personaEngine
export type Persona = {
  tone: 'empathetic' | 'urgent' | 'neutral' | 'friendly' | 'professional';
  formality: 'informal' | 'neutral' | 'formal';
  verbosity: 'concise' | 'standard' | 'elaborate';
  language: string;
  styleNotes: string[];
};

const apiKey = process.env.OPENAI_API_KEY;
let openai: OpenAI | null = null;
if (apiKey) {
  openai = new OpenAI({ apiKey });
}

export async function generateResponse(args: {
  customerText: string;
  persona: Persona;
  docs: Array<{ id: string; text: string; sourceId?: string; uri?: string }>;
  locale: string;
  channel: 'chat' | 'email' | 'sms' | 'voice';
}) {
  const { customerText, persona, docs } = args;

  // PROMPT ENGINEERING TECHNIQUE: Few-Shot Learning
  // Demonstrates providing examples to guide the model's response pattern
  const fewShotExamples = `
Here are examples of how to respond in different scenarios:

Customer: "I'm so frustrated with this product!"
Assistant: "I completely understand your frustration. Let me help you resolve this quickly. [Provide specific solution]"

Customer: "How do I reset my password?"
Assistant: "I'll guide you through the password reset process step by step. [Provide clear steps]"

Customer: "This is urgent, I need help now!"
Assistant: "I understand this is urgent. Let me get you the fastest solution. [Provide immediate action]"
`;

  // PROMPT ENGINEERING TECHNIQUE: Chain-of-Thought (CoT)
  // Demonstrates breaking down complex reasoning into steps
  const chainOfThoughtPrompt = `
Let me think through this step by step:
1. First, I need to understand what the customer is asking for
2. Then, I should check if we have relevant documentation
3. Next, I'll consider the customer's emotional state and urgency
4. Finally, I'll craft a response that matches the persona and addresses their needs

Customer request: ${customerText}
Available documentation: ${docs.length} relevant documents
Customer persona: ${persona.tone} tone, ${persona.formality} formality, ${persona.verbosity} verbosity
`;

  // PROMPT ENGINEERING TECHNIQUE: ReAct (Reasoning + Acting)
  // Demonstrates reasoning about the situation and taking appropriate action
  const reActPrompt = `
Let me reason about this situation and take appropriate action:

THOUGHT: The customer is expressing ${customerText}. I need to analyze their intent and emotional state.
OBSERVATION: Based on the available documentation, I have ${docs.length} relevant resources.
REASONING: The customer needs ${persona.verbosity === 'concise' ? 'a quick, direct answer' : persona.verbosity === 'elaborate' ? 'a detailed explanation' : 'a balanced response'}.
ACTION: I will provide a response that is ${persona.tone} and ${persona.formality}.
`;

  // PROMPT ENGINEERING TECHNIQUE: Self-Consistency
  // Demonstrates generating multiple responses and selecting the best one
  const selfConsistencyPrompts = [
    `Generate a ${persona.tone} response to: ${customerText}`,
    `Create a ${persona.formality} reply for: ${customerText}`,
    `Provide a ${persona.verbosity} answer to: ${customerText}`
  ];

  // PROMPT ENGINEERING TECHNIQUE: Self-Critique
  // Demonstrates asking the model to evaluate its own response
  const selfCritiquePrompt = `
After providing your response, evaluate it using these criteria:
1. Does it match the required tone (${persona.tone})?
2. Is it appropriately ${persona.formality}?
3. Is the verbosity level correct (${persona.verbosity})?
4. Does it address the customer's actual need?
5. Is it actionable and helpful?

Rate each criterion 1-5 and suggest improvements if needed.
`;

  // PROMPT ENGINEERING TECHNIQUE: Reflective Prompting
  // Demonstrates asking the model to reflect on its approach
  const reflectivePrompt = `
Before responding, take a moment to reflect:
- What is the customer really asking for?
- What emotions might they be experiencing?
- How can I best serve them given the available information?
- What would be most helpful in this specific context?

Now provide your response with this reflection in mind.
`;

  // PROMPT ENGINEERING TECHNIQUE: Tree-of-Thoughts (ToT)
  // Demonstrates exploring multiple reasoning paths
  const treeOfThoughtsPrompt = `
Let me explore different approaches to help this customer:

Branch 1 - Direct Solution:
- Provide immediate answer based on documentation
- Pros: Quick, efficient
- Cons: May miss emotional needs

Branch 2 - Empathetic Approach:
- Acknowledge feelings first, then provide solution
- Pros: Builds rapport, addresses emotions
- Cons: Takes longer, may not be appropriate for urgent issues

Branch 3 - Educational Approach:
- Explain the process and reasoning
- Pros: Empowers customer, prevents future issues
- Cons: May be too detailed for simple questions

Based on the customer's tone and urgency, I'll choose the most appropriate branch.
`;

  // PROMPT ENGINEERING TECHNIQUE: Prompt Chaining
  // Demonstrates breaking complex tasks into sequential steps
  const promptChain = {
    step1: `Analyze the customer's request: "${customerText}". What is their primary need?`,
    step2: `Given the need identified in step 1, what information from our documentation is most relevant?`,
    step3: `Based on steps 1 and 2, craft a response that matches the persona: ${persona.tone}, ${persona.formality}, ${persona.verbosity}`,
    step4: `Review the response from step 3. Does it effectively address the customer's need while maintaining the required persona?`
  };

  // Combine all techniques into a comprehensive system prompt
  const systemPrompt = `You are an expert customer support assistant. Use these prompt engineering techniques:

${fewShotExamples}

${chainOfThoughtPrompt}

${reActPrompt}

${reflectivePrompt}

${treeOfThoughtsPrompt}

Persona Requirements:
- Tone: ${persona.tone}
- Formality: ${persona.formality}
- Verbosity: ${persona.verbosity}
- Language: ${persona.language}
- Style notes: ${persona.styleNotes.join(', ') || 'none'}

Channel-specific considerations:
- SMS: Be extremely concise
- Email: Can be more detailed
- Chat: Conversational but efficient
- Voice: Clear and easy to understand

${selfCritiquePrompt}`;

  const context = docs
    .map((d, i) => `Doc ${i + 1} (${d.sourceId || 'kb'}): ${d.text.substring(0, 600)}`)
    .join('\n');

  const userPrompt = `Customer says: ${customerText}\nRelevant docs:\n${context}`;

  if (openai) {
    try {
      // PROMPT ENGINEERING TECHNIQUE: Self-Consistency Implementation
      // Generate multiple responses and select the best one
      const responses = await Promise.all(
        selfConsistencyPrompts.map(async (prompt, index) => {
          const completion = await openai.chat.completions.create({
            model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: `${prompt}\n\n${userPrompt}` },
            ],
            temperature: 0.3 + (index * 0.1), // Vary temperature for diversity
          });
          return completion.choices[0]?.message?.content || '';
        })
      );

      // Select the best response based on persona match
      const bestResponse = selectBestResponse(responses, persona);
      
      // PROMPT ENGINEERING TECHNIQUE: Self-Critique Implementation
      const critique = await openai.chat.completions.create({
        model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
        messages: [
          { role: 'system', content: 'You are a quality assurance expert. Evaluate the following customer service response.' },
          { role: 'user', content: `Evaluate this response: "${bestResponse}"\n\n${selfCritiquePrompt}` },
        ],
        temperature: 0.1,
      });

      const critiqueText = critique.choices[0]?.message?.content || '';
      console.log('[generator] Self-critique:', critiqueText);

      return { 
        text: bestResponse, 
        citations: docs.map((d) => ({ sourceId: d.sourceId, uri: d.uri })),
        promptTechniques: {
          fewShot: true,
          chainOfThought: true,
          reAct: true,
          selfConsistency: true,
          selfCritique: true,
          reflective: true,
          treeOfThoughts: true,
          promptChaining: true
        }
      };
    } catch (e) {
      console.warn('[generator] openai failed, using fallback:', e);
    }
  }

  const text = fallback(customerText, persona, docs);
  return { 
    text, 
    citations: docs.map((d) => ({ sourceId: d.sourceId, uri: d.uri })),
    promptTechniques: { fallback: true }
  };
}

// Helper function to select the best response from multiple options
function selectBestResponse(responses: string[], persona: Persona): string {
  // Simple heuristic: prefer responses that match persona characteristics
  const scores = responses.map(response => {
    let score = 0;
    
    // Check tone match
    if (persona.tone === 'empathetic' && response.toLowerCase().includes('understand')) score += 2;
    if (persona.tone === 'urgent' && response.toLowerCase().includes('quick')) score += 2;
    if (persona.tone === 'professional' && response.toLowerCase().includes('professional')) score += 2;
    
    // Check verbosity match
    const wordCount = response.split(' ').length;
    if (persona.verbosity === 'concise' && wordCount < 50) score += 3;
    if (persona.verbosity === 'standard' && wordCount >= 50 && wordCount < 150) score += 3;
    if (persona.verbosity === 'elaborate' && wordCount >= 150) score += 3;
    
    // Check formality match
    if (persona.formality === 'formal' && response.includes('I would be happy to')) score += 2;
    if (persona.formality === 'informal' && response.includes('Hey')) score += 2;
    
    return score;
  });
  
  const bestIndex = scores.indexOf(Math.max(...scores));
  return responses[bestIndex] || responses[0];
}

function fallback(customerText: string, persona: Persona, docs: Array<{ text: string }>): string {
  const ack = persona.tone === 'empathetic' ? "I understand how frustrating this can feel. " : '';
  const kb = docs.length ? `Here's what I found that may help: ${docs[0].text.substring(0, 220)}` : '';
  const concise = persona.verbosity === 'concise';
  const reply = `${ack}${concise ? '' : 'Thanks for reaching out. '}\n${kb}\nIf this doesn't resolve it, I can guide you step-by-step.`.trim();
  return reply;
}
