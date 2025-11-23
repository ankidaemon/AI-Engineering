import { Router } from 'express';
import { z } from 'zod';
import { demonstrateAllTechniques } from '../services/advancedPromptEngineering.js';

const router = Router();

// Demo request schema
const DemoRequest = z.object({
  query: z.string().min(1, 'Query is required'),
  technique: z.enum(['all', 'fewShot', 'chainOfThought', 'reAct', 'selfConsistency', 'selfCritique', 'reflective', 'treeOfThoughts', 'promptChaining']).default('all'),
  persona: z.object({
    tone: z.enum(['empathetic', 'urgent', 'neutral', 'friendly', 'professional']).default('neutral'),
    formality: z.enum(['informal', 'neutral', 'formal']).default('neutral'),
    verbosity: z.enum(['concise', 'standard', 'elaborate']).default('standard')
  }).default({
    tone: 'neutral',
    formality: 'neutral',
    verbosity: 'standard'
  })
});

// Example queries for students to test
const EXAMPLE_QUERIES = [
  "I can't log into my account and I'm really frustrated",
  "How do I reset my password?",
  "Your product is too expensive for me",
  "I need help with a technical issue right now",
  "Can you explain how the refund process works?",
  "I'm having trouble understanding the documentation"
];

/**
 * Demo endpoint to test prompt engineering techniques
 * Educational purpose: Students can see how different techniques produce different responses
 */
router.post('/test-techniques', async (req, res, next) => {
  try {
    const input = DemoRequest.parse(req.body);
    
    console.log(`[demo] Testing ${input.technique} technique with query: "${input.query}"`);
    
    const context = {
      persona: input.persona,
      docs: [
        { id: '1', text: 'Password reset can be done through the account settings page or by contacting support.' },
        { id: '2', text: 'Refunds are processed within 5-7 business days after approval.' }
      ],
      profile: {
        preferredLanguage: 'en',
        formalityPreference: input.persona.formality
      },
      history: []
    };

    let result;
    
    if (input.technique === 'all') {
      // Demonstrate all techniques
      result = await demonstrateAllTechniques(input.query, context);
    } else {
      // Import individual functions for specific technique testing
      const { 
        fewShotPrompting, 
        chainOfThoughtPrompting, 
        reActPrompting, 
        selfConsistencyPrompting,
        selfCritiquePrompting,
        reflectivePrompting,
        treeOfThoughtsPrompting,
        promptChaining
      } = await import('../services/advancedPromptEngineering.js');
      
      switch (input.technique) {
        case 'fewShot':
          result = { fewShot: await fewShotPrompting(input.query, input.persona) };
          break;
        case 'chainOfThought':
          result = { chainOfThought: await chainOfThoughtPrompting(input.query, context) };
          break;
        case 'reAct':
          result = { reAct: await reActPrompting(input.query, context.docs) };
          break;
        case 'selfConsistency':
          result = { selfConsistency: await selfConsistencyPrompting(input.query, input.persona) };
          break;
        case 'selfCritique':
          const tempResponse = "Thank you for contacting us. I understand your concern.";
          result = { selfCritique: await selfCritiquePrompting(tempResponse, input.persona) };
          break;
        case 'reflective':
          result = { reflective: await reflectivePrompting(input.query, context) };
          break;
        case 'treeOfThoughts':
          result = { treeOfThoughts: await treeOfThoughtsPrompting(input.query, input.persona) };
          break;
        case 'promptChaining':
          result = { promptChaining: await promptChaining(input.query, context) };
          break;
      }
    }

    return res.json({
      success: true,
      technique: input.technique,
      query: input.query,
      persona: input.persona,
      results: result,
      educationalNotes: {
        technique: input.technique,
        description: getTechniqueDescription(input.technique),
        useCase: getTechniqueUseCase(input.technique),
        tips: getTechniqueTips(input.technique)
      }
    });
  } catch (error) {
    next(error);
  }
});

/**
 * Get example queries for students to test
 */
router.get('/example-queries', (req, res) => {
  res.json({
    success: true,
    queries: EXAMPLE_QUERIES.map((query, index) => ({
      id: index + 1,
      query,
      description: getQueryDescription(query)
    })),
    educationalNotes: {
      purpose: "These example queries are designed to test different aspects of prompt engineering techniques",
      testingStrategy: "Try the same query with different techniques to see how responses vary",
      learningObjective: "Understand when and how to use each technique effectively"
    }
  });
});

/**
 * Get information about available techniques
 */
router.get('/techniques', (req, res) => {
  res.json({
    success: true,
    techniques: {
      all: {
        name: "All Techniques",
        description: "Demonstrates all prompt engineering techniques with the same query",
        useCase: "Educational comparison and learning"
      },
      fewShot: {
        name: "Few-Shot Learning",
        description: "Teaching the model by providing examples",
        useCase: "Consistent response patterns, style matching"
      },
      chainOfThought: {
        name: "Chain-of-Thought (CoT)",
        description: "Breaking down reasoning into explicit steps",
        useCase: "Complex problem-solving, logical reasoning"
      },
      reAct: {
        name: "ReAct (Reasoning + Acting)",
        description: "Structured reasoning with Thought-Observation-Action cycles",
        useCase: "Complex decision-making, structured analysis"
      },
      selfConsistency: {
        name: "Self-Consistency",
        description: "Generating multiple responses and selecting the best one",
        useCase: "Improving response quality, reducing randomness"
      },
      selfCritique: {
        name: "Self-Critique",
        description: "Asking the model to evaluate its own response",
        useCase: "Quality assurance, continuous improvement"
      },
      reflective: {
        name: "Reflective Prompting",
        description: "Deep reflection before responding",
        useCase: "Complex situations, emotional intelligence"
      },
      treeOfThoughts: {
        name: "Tree-of-Thoughts (ToT)",
        description: "Exploring multiple reasoning paths",
        useCase: "Complex decision-making, strategic thinking"
      },
      promptChaining: {
        name: "Prompt Chaining",
        description: "Breaking complex tasks into sequential steps",
        useCase: "Multi-step processes, complex analysis"
      }
    }
  });
});

// Helper functions for educational content
function getTechniqueDescription(technique: string): string {
  const descriptions: Record<string, string> = {
    all: "Demonstrates all prompt engineering techniques to show how they work together",
    fewShot: "Uses examples to teach the model specific response patterns",
    chainOfThought: "Breaks down complex reasoning into explicit, step-by-step thinking",
    reAct: "Structures reasoning as Thought-Observation-Action cycles for systematic problem-solving",
    selfConsistency: "Generates multiple responses and selects the best one for improved reliability",
    selfCritique: "Asks the model to evaluate its own response for quality assurance",
    reflective: "Encourages deep reflection before responding for better understanding",
    treeOfThoughts: "Explores multiple reasoning paths before choosing the best approach",
    promptChaining: "Breaks complex tasks into sequential, manageable steps"
  };
  return descriptions[technique] || "Advanced prompt engineering technique";
}

function getTechniqueUseCase(technique: string): string {
  const useCases: Record<string, string> = {
    all: "Educational comparison and learning about different techniques",
    fewShot: "Teaching consistent response patterns and styles",
    chainOfThought: "Complex problem-solving requiring logical reasoning",
    reAct: "Structured decision-making and analysis",
    selfConsistency: "Improving response quality and reducing randomness",
    selfCritique: "Quality assurance and continuous improvement",
    reflective: "Complex situations requiring deep understanding and empathy",
    treeOfThoughts: "Strategic thinking with multiple valid approaches",
    promptChaining: "Multi-step processes and complex analysis tasks"
  };
  return useCases[technique] || "Various applications in AI systems";
}

function getTechniqueTips(technique: string): string[] {
  const tips: Record<string, string[]> = {
    all: [
      "Compare responses from different techniques to understand their strengths",
      "Notice how different techniques handle the same query differently",
      "Consider which technique would be best for specific scenarios"
    ],
    fewShot: [
      "Provide diverse examples that cover different scenarios",
      "Ensure examples match the desired tone and style",
      "Use examples that are relevant to your specific use case"
    ],
    chainOfThought: [
      "Break down reasoning into clear, logical steps",
      "Make your thinking process explicit and transparent",
      "Use numbered or bulleted lists for clarity"
    ],
    reAct: [
      "Structure your reasoning into clear phases",
      "Be explicit about observations and reasoning",
      "Connect thoughts to actions logically"
    ],
    selfConsistency: [
      "Vary parameters (temperature, prompts) for diversity",
      "Use a scoring system to select the best response",
      "Consider multiple criteria when evaluating responses"
    ],
    selfCritique: [
      "Define clear evaluation criteria",
      "Ask for specific feedback and improvements",
      "Use the critique to refine future responses"
    ],
    reflective: [
      "Ask deep, probing questions",
      "Consider emotional and contextual factors",
      "Encourage empathy and understanding"
    ],
    treeOfThoughts: [
      "Explore multiple valid approaches",
      "Consider pros and cons of each approach",
      "Choose the most appropriate approach for the situation"
    ],
    promptChaining: [
      "Break complex tasks into manageable steps",
      "Use output from one step as input to the next",
      "Ensure each step builds logically on the previous"
    ]
  };
  return tips[technique] || ["Experiment with different approaches", "Test and iterate on your prompts"];
}

function getQueryDescription(query: string): string {
  if (query.includes("frustrated")) return "Tests emotional handling and empathy";
  if (query.includes("password")) return "Tests procedural knowledge and step-by-step guidance";
  if (query.includes("expensive")) return "Tests objection handling and value communication";
  if (query.includes("right now")) return "Tests urgency and immediate response needs";
  if (query.includes("explain")) return "Tests educational and explanatory capabilities";
  if (query.includes("trouble understanding")) return "Tests simplification and clarity";
  return "General customer service scenario";
}

export { router };
