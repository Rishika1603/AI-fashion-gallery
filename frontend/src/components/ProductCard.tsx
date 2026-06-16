import React, { useState } from 'react';
import { Heart, ShoppingBag, Shirt } from 'lucide-react';
import type { Product } from '../types';
import { motion } from 'framer-motion';
import TryOnModal from './TryOnModal';
import ProductDetailModal from './ProductDetailModal';
import { tryOn } from '../api';

interface ProductCardProps {
    product: Product;
    onDesign?: (product: Product) => void;
    isResult?: boolean;
    matchScore?: number;
}

const ProductCard: React.FC<ProductCardProps> = ({ product, onDesign, isResult, matchScore }) => {
    const [isLiked, setIsLiked] = useState(false);
    const [isTryOnOpen, setIsTryOnOpen] = useState(false);
    const [isDetailOpen, setIsDetailOpen] = useState(false);

    const handleTryOnRequest = async (file: File) => {
        return await tryOn(file, product.image_url);
    };

    return (
        <>
            <motion.div
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ y: -8, scale: 1.02 }}
                onClick={() => setIsDetailOpen(true)}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                className="glass-card group cursor-pointer overflow-hidden rounded-3xl"
            >
                <div className="relative aspect-[3/4] overflow-hidden">
                    <img
                        src={product.image_url}
                        alt={product.name}
                        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110 group-hover:rotate-1"
                    />

                    {/* Gradient Overlay on Hover */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                    {/* Social Signal Badge */}
                    {product.social_label && (
                        <div className="absolute top-3 left-3 bg-white/90 backdrop-blur-md px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider text-brand-dark shadow-sm ring-1 ring-black/5">
                            {product.social_label}
                        </div>
                    )}

                    {/* Match Score for Results */}
                    {isResult && matchScore && (
                        <div className="absolute top-3 right-3 bg-brand-secondary text-white px-3 py-1 rounded-full text-[10px] font-bold shadow-lg animate-pulse">
                            {Math.round(matchScore * 100)}% Match
                        </div>
                    )}

                    {/* Favorite Button */}
                    <motion.button
                        whileTap={{ scale: 0.8 }}
                        onClick={(e) => { e.stopPropagation(); setIsLiked(!isLiked); }}
                        className={`absolute bottom-4 right-4 p-3 rounded-full backdrop-blur-md transition-all shadow-lg ${isLiked
                            ? 'bg-violet-500 text-white'
                            : 'bg-black/40 text-white hover:bg-violet-500/80 border border-white/20'
                            }`}
                    >
                        <Heart size={20} fill={isLiked ? "currentColor" : "none"} />
                    </motion.button>
                </div>

                <div className="p-5 relative z-10 flex flex-col gap-3">
                    <div className="flex justify-between items-start">
                        <h3 className="font-semibold text-white text-base truncate flex-1 leading-tight tracking-wide">{product.name}</h3>
                        <span className="text-xs text-slate-500 ml-2 font-mono uppercase bg-white/5 px-2 py-1 rounded-md">{product.style_code}</span>
                    </div>

                    <div className="flex items-center gap-3">
                        <span className="font-bold text-xl text-violet-400">${product.price_min.toFixed(0)}</span>
                        {product.price_max > product.price_min && (
                            <span className="text-sm text-slate-500 line-through decoration-violet-500/50">${product.price_max.toFixed(0)}</span>
                        )}
                    </div>

                    {/* Color Swatches */}
                    <div className="flex gap-2 max-w-full overflow-hidden">
                        {product.color_swatches.map((color, idx) => (
                            <div
                                key={`${color}-${idx}`}
                                className="w-5 h-5 rounded-full border border-white/20 shadow-inner hover:scale-125 transition-transform cursor-help"
                                style={{ backgroundColor: color }}
                                title={color}
                            />
                        ))}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 mt-2">
                        {/* Try On Button */}
                        <button
                            onClick={(e) => { e.stopPropagation(); setIsTryOnOpen(true); }}
                            className="flex-1 py-3 bg-white/5 hover:bg-white/10 text-white rounded-2xl font-medium text-sm flex items-center justify-center gap-2 transition-all duration-300 border border-white/10 hover:border-white/20"
                        >
                            <Shirt size={16} />
                            Try On
                        </button>

                        {/* Primary CTA */}
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                if (isResult) {
                                    onDesign?.(product);
                                } else {
                                    setIsDetailOpen(true);
                                }
                            }}
                            className="flex-1 py-3 bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white rounded-2xl font-medium text-sm flex items-center justify-center gap-2 transition-all duration-300 shadow-lg shadow-violet-500/25"
                        >
                            <ShoppingBag size={16} />
                            {isResult ? 'Design' : 'View'}
                        </button>
                    </div>
                </div>
            </motion.div>

            {/* Product Detail Modal */}
            <ProductDetailModal
                isOpen={isDetailOpen}
                onClose={() => setIsDetailOpen(false)}
                product={product}
                onTryOn={() => setIsTryOnOpen(true)}
            />

            {/* Try On Modal */}
            <TryOnModal
                isOpen={isTryOnOpen}
                onClose={() => setIsTryOnOpen(false)}
                productImage={product.image_url}
                onTryOn={handleTryOnRequest}
            />
        </>
    );
};

export default ProductCard;
