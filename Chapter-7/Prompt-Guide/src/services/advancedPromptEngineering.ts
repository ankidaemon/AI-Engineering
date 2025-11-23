import OpenAI from 'openai';

const apiKey = process.env.OPENAI_API_KEY;
let openai: OpenAI | null = null;
if (apiKey) {
  openai = new OpenAI({ apiKey });
}

/**
 * ADVANCED PROMPT ENGINEERING TECHNIQUES FOR EDUCATIONAL PURPOSES
 * 
 * This file demonstrates various prompt engineering techniques that students
 * can learn from and apply in their own projects.
 */

// PROMPT ENGINEERING TECHNIQUE 1: Few-Shot Learning
// Purpose: Teach the model by providing examples of input-output pairs
export async function fewShotPrompting(customerQuery: string, persona: any) {
  const fewShotPrompt = `
You are a customer service agent. Here are examples of how to respond:

Customer: "I can't log into my account"
Assistant: "I understand this can be frustrating. Let me help you get back into your account. First, try clicking the 'Forgot Password' link on the login page. If that doesn't work, I can guide you through additional steps."

Customer: "Your product is too expensive"
Assistant: "I appreciate you sharing your feedback about pricing. We offer several options to make our product more accessible, including payment plans and discounts for certain customers. Would you like me to check if you qualify for any special pricing?"

Customer: "How do I cancel my subscription?"
Assistant: "I'll help you cancel your subscription. You can do this through your account settings, or I can walk you through the process step by step. Would you prefer to do it yourself, or would you like me to assist you?"

Now respond to this customer query: "${customerQuery}"
Persona: ${persona.tone} tone, ${persona.formality} formality
`;

  if (openai) {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: fewShotPrompt }],
      temperature: 0.3,
    });
    return completion.choices[0]?.message?.content;
  }
  return "Few-shot example response";
}

// PROMPT ENGINEERING TECHNIQUE 2: Chain-of-Thought (CoT)
// Purpose: Break down complex reasoning into explicit steps
export async function chainOfThoughtPrompting(customerQuery: string, context: any) {
  const cotPrompt = `
Let me think through this step by step:

1. First, I need to understand what the customer is asking for
   - Customer says: "${customerQuery}"
   - I should identify the main request and any underlying needs

2. Next, I should consider the available context
   - Available documentation: ${context.docs?.length || 0} documents
   - Customer profile: ${context.profile ? 'Available' : 'Not available'}
   - Previous interactions: ${context.history ? 'Available' : 'Not available'}

3. Then, I need to determine the best approach
   - What type of response would be most helpful?
   - Should I provide immediate answers or guide them through a process?
   - Do they need emotional support or just information?

4. Finally, I'll craft my response
   - Make sure it addresses their primary need
   - Use appropriate tone and formality
   - Include relevant information from available resources

Based on this reasoning, here's my response:
`;

  if (openai) {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: cotPrompt }],
      temperature: 0.2,
    });
    return completion.choices[0]?.message?.content;
  }
  return "Chain-of-thought reasoning response";
}

// PROMPT ENGINEERING TECHNIQUE 3: ReAct (Reasoning + Acting)
// Purpose: Structure reasoning as Thought-Observation-Action cycles
export async function reActPrompting(customerQuery: string, availableDocs: any[]) {
  const reActPrompt = `
Use the ReAct format to respond to this customer query: "${customerQuery}"

THOUGHT: I need to analyze what the customer is asking for and determine the best way to help them.

OBSERVATION: I have ${availableDocs.length} relevant documents available that might help answer their question.

REASONING: Based on the customer's query and available resources, I should provide a response that directly addresses their need while using relevant information from our documentation.

ACTION: I will craft a response that:
1. Acknowledges their request
2. Provides the most relevant information from available docs
3. Offers next steps if needed

Now provide your response following this reasoning:
`;

  if (openai) {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: reActPrompt }],
      temperature: 0.3,
    });
    return completion.choices[0]?.message?.content;
  }
  return "ReAct structured response";
}

// PROMPT ENGINEERING TECHNIQUE 4: Self-Consistency
// Purpose: Generate multiple responses and select the best one
export async function selfConsistencyPrompting(customerQuery: string, persona: any) {
  const prompts = [
    `Generate a ${persona.tone} response to: "${customerQuery}"`,
    `Create a ${persona.formality} reply for: "${customerQuery}"`,
    `Provide a ${persona.verbosity} answer to: "${customerQuery}"`,
    `Respond to "${customerQuery}" in a helpful and professional manner`,
    `Answer "${customerQuery}" with empathy and understanding`
  ];

  if (openai) {
    const responses = await Promise.all(
      prompts.map(async (prompt, index) => {
        const completion = await openai.chat.completions.create({
          model: 'gpt-4o-mini',
          messages: [{ role: 'user', content: prompt }],
          temperature: 0.3 + (index * 0.1), // Vary temperature for diversity
        });
        return completion.choices[0]?.message?.content || '';
      })
    );

    // Select the best response (in practice, you might use more sophisticated selection)
    return selectBestResponse(responses, persona);
  }
  return "Self-consistency selected response";
}

// PROMPT ENGINEERING TECHNIQUE 5: Self-Critique
// Purpose: Ask the model to evaluate its own response
export async function selfCritiquePrompting(originalResponse: string, requirements: any) {
  const critiquePrompt = `
You are a quality assurance expert. Evaluate the following customer service response:

RESPONSE: "${originalResponse}"

EVALUATION CRITERIA:
1. Does it match the required tone (${requirements.tone})?
2. Is it appropriately ${requirements.formality}?
3. Is the verbosity level correct (${requirements.verbosity})?
4. Does it address the customer's actual need?
5. Is it actionable and helpful?
6. Does it use available information effectively?

Rate each criterion 1-5 and provide specific feedback for improvement.
`;

  if (openai) {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: critiquePrompt }],
      temperature: 0.1,
    });
    return completion.choices[0]?.message?.content;
  }
  return "Self-critique evaluation";
}

// PROMPT ENGINEERING TECHNIQUE 6: Reflective Prompting
// Purpose: Ask the model to reflect on its approach before responding
export async function reflectivePrompting(customerQuery: string, context: any) {
  const reflectivePrompt = `
Before responding to the customer, take a moment to reflect:

REFLECTION QUESTIONS:
1. What is the customer really asking for? (Look beyond the surface question)
2. What emotions might they be experiencing? (Consider tone, urgency, context)
3. What would be most helpful in this specific situation? (Consider their needs, available resources, constraints)
4. How can I best serve them given the available information? (Think about what I know and what I can offer)
5. What might be the underlying cause of their issue? (Consider root causes, not just symptoms)

Customer Query: "${customerQuery}"
Available Context: ${JSON.stringify(context, null, 2)}

Now provide your response with this reflection in mind:
`;

  if (openai) {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: reflectivePrompt }],
      temperature: 0.4,
    });
    return completion.choices[0]?.message?.content;
  }
  return "Reflective response";
}

// PROMPT ENGINEERING TECHNIQUE 7: Tree-of-Thoughts (ToT)
// Purpose: Explore multiple reasoning paths before choosing the best approach
export async function treeOfThoughtsPrompting(customerQuery: string, persona: any) {
  const totPrompt = `
Let me explore different approaches to help this customer:

TREE OF THOUGHTS ANALYSIS:

Branch 1 - Direct Solution Approach:
- Provide immediate, factual answer
- Pros: Quick, efficient, gets to the point
- Cons: May miss emotional needs, could seem cold
- Best for: Simple questions, urgent issues, factual requests

Branch 2 - Empathetic Support Approach:
- Acknowledge feelings first, then provide solution
- Pros: Builds rapport, addresses emotional needs, shows care
- Cons: Takes longer, may not be appropriate for urgent issues
- Best for: Frustrated customers, complex problems, relationship building

Branch 3 - Educational Approach:
- Explain the process and reasoning behind the solution
- Pros: Empowers customer, prevents future issues, builds understanding
- Cons: May be too detailed for simple questions, could overwhelm
- Best for: Learning opportunities, complex processes, prevention

Branch 4 - Collaborative Problem-Solving:
- Work with the customer to find the best solution together
- Pros: Customer feels involved, solution is tailored, builds trust
- Cons: Takes time, requires customer engagement, may not work for simple issues
- Best for: Complex problems, relationship building, when multiple options exist

Customer Query: "${customerQuery}"
Persona: ${persona.tone} tone, ${persona.formality} formality, ${persona.verbosity} verbosity

Based on this analysis, I'll choose the most appropriate branch and provide my response:
`;

  if (openai) {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: totPrompt }],
      temperature: 0.3,
    });
    return completion.choices[0]?.message?.content;
  }
  return "Tree-of-thoughts analyzed response";
}

// PROMPT ENGINEERING TECHNIQUE 8: Prompt Chaining
// Purpose: Break complex tasks into sequential steps
export async function promptChaining(customerQuery: string, context: any) {
  if (!openai) return "Prompt chaining response";

  // Step 1: Analyze the customer's request
  const step1 = await openai.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [{ 
      role: 'user', 
      content: `Analyze this customer request: "${customerQuery}". What is their primary need? What emotions are they expressing? What type of help do they need?` 
    }],
    temperature: 0.2,
  });

  const analysis = step1.choices[0]?.message?.content || '';

  // Step 2: Identify relevant information
  const step2 = await openai.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [{ 
      role: 'user', 
      content: `Based on this analysis: "${analysis}", what information from our knowledge base would be most relevant? Available docs: ${context.docs?.length || 0} documents.` 
    }],
    temperature: 0.2,
  });

  const relevantInfo = step2.choices[0]?.message?.content || '';

  // Step 3: Craft the response
  const step3 = await openai.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [{ 
      role: 'user', 
      content: `Based on the analysis: "${analysis}" and relevant information: "${relevantInfo}", craft a helpful response to the customer's original query: "${customerQuery}"` 
    }],
    temperature: 0.3,
  });

  return step3.choices[0]?.message?.content || 'Prompt chaining response';
}

// Helper function for self-consistency
function selectBestResponse(responses: string[], persona: any): string {
  // Simple scoring system - in practice, you might use more sophisticated methods
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
    
    return score;
  });
  
  const bestIndex = scores.indexOf(Math.max(...scores));
  return responses[bestIndex] || responses[0];
}

// Educational function to demonstrate all techniques
export async function demonstrateAllTechniques(customerQuery: string, context: any) {
  console.log('=== PROMPT ENGINEERING TECHNIQUES DEMONSTRATION ===');
  
  const results: any = {
    fewShot: await fewShotPrompting(customerQuery, context.persona),
    chainOfThought: await chainOfThoughtPrompting(customerQuery, context),
    reAct: await reActPrompting(customerQuery, context.docs || []),
    selfConsistency: await selfConsistencyPrompting(customerQuery, context.persona),
    reflective: await reflectivePrompting(customerQuery, context),
    treeOfThoughts: await treeOfThoughtsPrompting(customerQuery, context.persona),
    promptChaining: await promptChaining(customerQuery, context)
  };

  // Demonstrate self-critique on one of the responses
  const fewShotResponse = results.fewShot || "Sample response for critique";
  results.selfCritique = await selfCritiquePrompting(fewShotResponse, context.persona);

  return results;
}
