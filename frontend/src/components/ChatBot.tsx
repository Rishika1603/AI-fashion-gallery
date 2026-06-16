import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { chatWithBot, getProduct, tryOn } from '../api';
import ReactMarkdown from 'react-markdown';
import type { Product } from '../types';
import TryOnModal from './TryOnModal';
import ProductDetailModal from './ProductDetailModal';

interface Message {
    id: string;
    sender: 'user' | 'bot';
    text: string;
}

const ChatBot: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([
        { id: 'welcome', sender: 'bot', text: 'Hi! I can help you find products or answer fashion questions. What are you looking for?' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
    const [isTryOnOpen, setIsTryOnOpen] = useState(false);
    const [isDetailOpen, setIsDetailOpen] = useState(false);
    const [isProductLoading, setIsProductLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isOpen]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg: Message = { id: Date.now().toString(), sender: 'user', text: input };
        const currentMessages = [...messages, userMsg];
        setMessages(currentMessages);
        setInput('');
        setIsLoading(true);

        // Prepare history for API (exclude the welcome message if desired, but here we include all)
        const history = messages
            .filter(msg => msg.id !== 'welcome') // Optional: skip welcome message
            .map(msg => ({
                role: msg.sender === 'user' ? 'user' : 'assistant',
                content: msg.text
            }));

        try {
            const response = await chatWithBot(input, history);
            const botMsg: Message = {
                id: (Date.now() + 1).toString(),
                sender: 'bot',
                text: response.response
            };
            setMessages(prev => [...prev, botMsg]);
        } catch (error) {
            console.error(error);
            setMessages(prev => [...prev, {
                id: Date.now().toString(),
                sender: 'bot',
                text: "Sorry, I'm having trouble connecting right now."
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleLinkClick = async (e: React.MouseEvent, href: string) => {
        if (href.startsWith('product:')) {
            e.preventDefault();
            const productId = href.split(':')[1];
            if (productId) {
                setIsProductLoading(true);
                try {
                    const product = await getProduct(productId);
                    setSelectedProduct(product);
                    setIsDetailOpen(true);
                } catch (error) {
                    console.error("Failed to load product", error);
                } finally {
                    setIsProductLoading(false);
                }
            }
        }
    };

    const handleTryOnRequest = async (file: File) => {
        if (!selectedProduct) return new Blob();
        return await tryOn(file, selectedProduct.image_url);
    };

    return (
        <div className="fixed bottom-6 right-6 z-[60] flex flex-col items-end">
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="mb-6 w-[350px] md:w-[400px] glass-card bg-black/60 rounded-[2rem] shadow-2xl overflow-hidden border border-white/10 flex flex-col"
                    >
                        {/* Header */}
                        <div className="bg-gradient-to-r from-violet-600/50 to-cyan-600/50 text-white p-5 flex justify-between items-center premium-blur border-b border-white/10">
                            <h3 className="font-bold text-lg flex items-center gap-2">
                                <span className="text-xl">✨</span> Fashion AI
                            </h3>
                            <button
                                onClick={() => setIsOpen(false)}
                                className="w-8 h-8 flex items-center justify-center rounded-full bg-black/20 hover:bg-black/40 text-white/80 hover:text-white transition-colors"
                            >
                                ✕
                            </button>
                        </div>

                        {/* Messages */}
                        <div className="h-[400px] overflow-y-auto p-5 bg-transparent flex flex-col gap-4 scrollbar-hide">
                            {messages.map((msg) => (
                                <div
                                    key={msg.id}
                                    className={`max-w-[85%] p-4 rounded-2xl text-[15px] leading-relaxed premium-blur ${msg.sender === 'user'
                                        ? 'bg-gradient-to-r from-violet-600 to-cyan-600 text-white self-end rounded-br-sm shadow-lg shadow-violet-500/20'
                                        : 'bg-white/10 border border-white/10 text-slate-200 self-start rounded-bl-sm shadow-lg markdown-container'
                                        }`}
                                >
                                    {msg.sender === 'bot' ? (
                                        <ReactMarkdown
                                            urlTransform={(uri) => uri} // Allow custom product: protocol
                                            components={{
                                                a: ({ node, ...props }) => {
                                                    console.log("Rendering link props:", props);
                                                    return (
                                                        <a
                                                            {...props}
                                                            onClick={(e) => handleLinkClick(e, props.href || '')}
                                                            className="text-cyan-400 font-bold hover:text-cyan-300 cursor-pointer transition-colors underline decoration-cyan-400/30 underline-offset-2"
                                                        />
                                                    );
                                                },
                                                p: ({ node, ...props }) => <p {...props} className="mb-2 last:mb-0" />,
                                                ul: ({ node, ...props }) => <ul {...props} className="list-disc ml-4 mb-2" />,
                                                li: ({ node, ...props }) => <li {...props} className="mb-1" />,
                                            }}
                                        >
                                            {msg.text}
                                        </ReactMarkdown>
                                    ) : (
                                        <p>{msg.text}</p>
                                    )}
                                </div>
                            ))}
                            {isLoading && (
                                <div className="self-start bg-white/5 border border-white/10 p-4 rounded-2xl rounded-bl-sm premium-blur">
                                    <div className="flex gap-1.5 p-1">
                                        <span className="w-2 h-2 bg-violet-400 rounded-full animate-bounce"></span>
                                        <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                                        <span className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input */}
                        <div className="p-4 border-t border-white/10 bg-white/5 premium-blur flex gap-3">
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                                placeholder="Ask me anything..."
                                className="flex-1 px-5 py-3 bg-black/50 border border-white/10 rounded-full text-white placeholder-slate-400 focus:outline-none focus:border-violet-500/50 transition-all font-medium"
                            />
                            <button
                                onClick={handleSend}
                                disabled={isLoading || !input.trim()}
                                className="w-12 h-12 bg-gradient-to-r from-violet-600 to-cyan-600 text-white rounded-full flex items-center justify-center disabled:opacity-50 disabled:grayscale hover:shadow-lg hover:shadow-violet-500/30 transition-all"
                            >
                                ➤
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Toggle Button */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsOpen(!isOpen)}
                className="w-16 h-16 bg-gradient-to-r from-violet-600 to-cyan-600 text-white rounded-full shadow-2xl shadow-violet-500/40 flex items-center justify-center text-3xl transition-transform border border-white/20 z-50"
            >
                {isOpen ? '✕' : '✨'}
            </motion.button>

            {/* Product Detail Modal */}
            {selectedProduct && (
                <ProductDetailModal
                    isOpen={isDetailOpen}
                    onClose={() => setIsDetailOpen(false)}
                    product={selectedProduct}
                    onTryOn={() => setIsTryOnOpen(true)}
                />
            )}

            {/* Try On Modal */}
            {selectedProduct && (
                <TryOnModal
                    isOpen={isTryOnOpen}
                    onClose={() => {
                        setIsTryOnOpen(false);
                        // Delay clearing product to allow outward animation
                        setTimeout(() => setSelectedProduct(null), 300);
                    }}
                    productImage={selectedProduct.image_url}
                    onTryOn={handleTryOnRequest}
                />
            )}

            {/* Loading Overlay */}
            <AnimatePresence>
                {isProductLoading && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] bg-black/80 premium-blur flex items-center justify-center"
                    >
                        <div className="flex flex-col items-center gap-4">
                            <Loader2 className="w-12 h-12 animate-spin text-violet-400" />
                            <p className="text-sm font-bold text-white uppercase tracking-widest animate-pulse">Fetching Look...</p>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default ChatBot;
