import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Shirt, ShoppingCart, Heart, ShieldCheck } from 'lucide-react';
import type { Product } from '../types';

interface ProductDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    product: Product;
    onTryOn: () => void;
}

const ProductDetailModal: React.FC<ProductDetailModalProps> = ({ isOpen, onClose, product, onTryOn }) => {
    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                {/* Backdrop */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                />

                {/* Modal Content */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9, y: 20 }}
                    className="relative glass-card bg-black/40 rounded-3xl w-full max-w-4xl overflow-hidden shadow-2xl flex flex-col md:flex-row h-full max-h-[85vh] md:max-h-[600px]"
                >
                    {/* Close Button */}
                    <button
                        onClick={onClose}
                        className="absolute top-4 right-4 z-10 w-10 h-10 bg-black/50 hover:bg-black border border-white/20 rounded-full flex items-center justify-center shadow-lg transition-colors"
                    >
                        <X size={20} className="text-white" />
                    </button>

                    {/* Left: Product Image */}
                    <div className="w-full md:w-1/2 h-64 md:h-auto relative overflow-hidden bg-white/5">
                        <img
                            src={product.image_url}
                            alt={product.name}
                            className="w-full h-full object-cover"
                        />
                        <div className="absolute top-4 left-4">
                            <span className="bg-white/10 premium-blur border border-white/20 text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-tighter">
                                {product.category}
                            </span>
                        </div>
                    </div>

                    {/* Right: Details */}
                    <div className="flex-1 p-6 md:p-8 flex flex-col overflow-y-auto">
                        <div className="flex justify-between items-start mb-2">
                            <h2 className="text-2xl md:text-3xl font-black text-white leading-tight">
                                {product.name}
                            </h2>
                            <button className="text-white/40 hover:text-rose-500 transition-colors">
                                <Heart size={24} />
                            </button>
                        </div>

                        <p className="text-violet-400/80 text-sm font-mono mb-6 uppercase tracking-widest">{product.style_code}</p>

                        <div className="flex items-center gap-3 mb-8">
                            <span className="text-3xl font-bold text-violet-400">${product.price_min.toFixed(0)}</span>
                            {product.price_max > product.price_min && (
                                <span className="text-xl text-slate-500 line-through">${product.price_max.toFixed(0)}</span>
                            )}
                        </div>

                        {/* Colors */}
                        <div className="mb-8">
                            <h4 className="text-sm font-bold text-slate-300 uppercase mb-3 tracking-wider">Available Colors</h4>
                            <div className="flex gap-3">
                                {product.color_swatches.map((color, idx) => (
                                    <div
                                        key={`${color}-${idx}`}
                                        className="w-8 h-8 rounded-full border border-white/20 shadow-inner transition-transform hover:scale-110 cursor-pointer"
                                        style={{ backgroundColor: color }}
                                        title={color}
                                    />
                                ))}
                            </div>
                        </div>

                        {/* Features */}
                        <div className="space-y-4 mb-8">
                            <div className="flex items-center gap-4 text-sm text-slate-300">
                                <div className="p-2 bg-emerald-500/10 rounded-lg">
                                    <ShieldCheck size={18} className="text-emerald-400" />
                                </div>
                                <span>Premium Fabric & Ethical Sourcing</span>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-slate-300">
                                <div className="p-2 bg-violet-500/10 rounded-lg">
                                    <Shirt size={18} className="text-violet-400" />
                                </div>
                                <span>Breathable material for all-day comfort</span>
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="mt-auto flex flex-col sm:flex-row gap-4">
                            <button
                                onClick={onTryOn}
                                className="flex-1 py-4 bg-white/5 border border-white/10 hover:border-white/30 text-white rounded-2xl font-bold flex items-center justify-center gap-2 hover:bg-white/10 transition-all active:scale-95"
                            >
                                <Shirt size={20} />
                                Virtual Try-On
                            </button>
                            <button
                                className="flex-1 py-4 bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white rounded-2xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-violet-500/25 transition-all active:scale-95"
                            >
                                <ShoppingCart size={20} />
                                Add to Cart
                            </button>
                        </div>
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
};

export default ProductDetailModal;
