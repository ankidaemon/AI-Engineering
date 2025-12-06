import React, { useState, useEffect, useRef } from 'react';

// Main App component
const App = () => {
    // State to hold the chat messages
    const [messages, setMessages] = useState([
        { sender: 'assistant', text: "Hello, how can I help you today? I'm ready to assist with any questions you have.", tone: '' },
    ]);
    // State for the user's input
    const [userInput, setUserInput] = useState('');
    // State to manage loading state for the assistant's response
    const [isLoading, setIsLoading] = useState(false);
    // Ref for the chat window to enable auto-scrolling
    const chatWindowRef = useRef(null);

    // Simulate an API call to a generative AI model
    const getAiResponse = async (userMessage) => {
        setIsLoading(true);

        const prompt = `
        You are a customer service agent. Analyze the customer's messages. 
        Do the Sentiment Analysis and set in field 'tone'. 
        Reply based on customers's sentiment and be extra polite if customer seems sad or angry or have negative sentiments.
        Return ONLY JSON:
        {
        "response": "<assistant reply>",
        "tone": "<Customer's tone>"
        }

        Customer: "${userMessage}"
        `;

        const payload = {
            model: "gpt-4.1-mini",
            input: prompt
        };

        const apiKey = "sk-proj-WqrI1AE7g9hvYohnc0R2B"; //your API key goes here. Get yours https://platform.openai.com/settings/organization/api-keys
        const apiUrl = "https://api.openai.com/v1/responses";

        const response = await fetch(apiUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${apiKey}`
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (!response.ok) {
            console.error(result);
            setIsLoading(false);
            return {
                text: "Sorry, something went wrong.",
                tone: "neutral"
            };
        }

        // Parse structured JSON from model
        const parsed = JSON.parse(result.output[0].content[0].text);

        setIsLoading(false);
        return {
            text: parsed.response,
            tone: parsed.tone
        };
    };

    // Handle sending a new message
    const handleSendMessage = async (e) => {
        e.preventDefault();
        const trimmedInput = userInput.trim();
        if (!trimmedInput) return;

        // Add user message to the chat
        const newUserMessage = { sender: 'user', text: trimmedInput };
        setMessages(prevMessages => [...prevMessages, newUserMessage]);
        setUserInput('');

        // Get and add AI response
        const aiResponse = await getAiResponse(trimmedInput);
        const newAiMessage = { sender: 'assistant', text: aiResponse.text, tone: aiResponse.tone };
        setMessages(prevMessages => [...prevMessages, newAiMessage]);
    };

    // Scroll to the bottom of the chat window on new messages
    useEffect(() => {
        if (chatWindowRef.current) {
            chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
        }
    }, [messages]);

    // Define Tailwind CSS classes for different tones
    const toneStyles = {
        friendly: "bg-emerald-100 text-emerald-800",
        professional: "bg-indigo-100 text-indigo-800",
        empathetic: "bg-rose-100 text-rose-800",
        happy: "bg-yellow-100 text-yellow-800",
        positive: "bg-green-100 text-green-800",
        sad: "bg-blue-100 text-blue-800",
        neutral: "bg-gray-100 text-gray-800",
        angry: "bg-red-100 text-red-800",
        negative: "bg-red-100 text-red-800",
        '': "bg-emerald-100 text-emerald-800",
    };

    return (
        <div className="flex flex-col h-screen bg-gray-100 font-sans p-4 antialiased">
            <div className="flex-grow flex flex-col max-w-2xl mx-auto w-full bg-white rounded-xl shadow-lg overflow-hidden">
                {/* Chat Header */}
                <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4 text-center">
                    <h1 className="text-xl font-bold tracking-wide">AI Customer Service Assistant</h1>
                    <p className="text-sm opacity-80 mt-1">Chat with our adaptive AI assistant</p>
                </div>

                {/* Chat Messages Window */}
                <div ref={chatWindowRef} className="flex-grow p-6 space-y-4 overflow-y-auto">
                    {messages.map((msg, index) => (
                        <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`p-4 rounded-3xl max-w-sm ${msg.sender === 'user'
                                ? 'bg-blue-500 text-white rounded-br-none'
                                : `${toneStyles[msg.tone]} rounded-bl-none`
                                }`}>
                                <p className="text-sm leading-relaxed">
                                    {msg.text}
                                </p>

                                {msg.sender === "assistant" && msg.tone && (
                                    <p className="text-xs mt-2 opacity-70">
                                        <strong>User Sentiment detected:</strong> {msg.tone}
                                    </p>
                                )}
                            </div>

                        </div>
                    ))}
                    {/* Loading indicator */}
                    {isLoading && (
                        <div className="flex justify-start">
                            <div className="p-4 rounded-3xl bg-gray-200 text-gray-800 rounded-bl-none">
                                <div className="flex items-center space-x-2">
                                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-150"></div>
                                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-300"></div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Message Input Form */}
                <form onSubmit={handleSendMessage} className="p-4 bg-gray-50 border-t border-gray-200">
                    <div className="flex space-x-2">
                        <input
                            type="text"
                            value={userInput}
                            onChange={(e) => setUserInput(e.target.value)}
                            placeholder="Type your message..."
                            className="flex-grow p-3 rounded-full bg-white border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200"
                            disabled={isLoading}
                        />
                        <button
                            type="submit"
                            className={`p-3 rounded-full text-white transition-all duration-200 shadow-md ${isLoading
                                ? 'bg-gray-400 cursor-not-allowed'
                                : 'bg-blue-600 hover:bg-blue-700 active:scale-95'
                                }`}
                            disabled={isLoading}
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                            </svg>
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default App;