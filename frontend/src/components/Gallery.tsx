import React, { useEffect, useState } from 'react';
import { Camera, Search as SearchIcon, ChevronDown } from 'lucide-react';
import type { Product } from '../types';
import { getProducts } from '../api';
import ProductCard from './ProductCard';
import { motion } from 'framer-motion';
import Lottie from 'lottie-react';
import heroAnimation from '../../animations/shopping-ecommerce.json';

interface GalleryProps {
    onStartSearch: () => void;
}

interface FilterOption {
    label: string;
    value: string;
}

const FILTERS: FilterOption[] = [
    { label: 'All', value: 'All' },
    { label: 'Tops', value: 'Tops' },
    { label: 'Bottoms', value: 'Bottoms' },
    { label: 'Blazers', value: 'Blazer' },
    { label: 'Hoodies', value: 'Hoodie' },
    { label: 'Jackets', value: 'Jacket' },
    { label: 'Denim Jackets', value: 'Denim Jacket' },
    { label: 'Sport Jackets', value: 'Sport Jacket' },
    { label: 'T-Shirts', value: 'T-Shirt' },
    { label: 'Shirts', value: 'Shirt' },
    { label: 'Polo Shirts', value: 'Polo Shirt' },
    { label: 'Sweaters', value: 'Sweater' },
    { label: 'Coats', value: 'Coat' },
    { label: 'Dresses', value: 'Dress' },
    { label: 'Trousers', value: 'Trousers' },
    { label: 'Shorts', value: 'Shorts' },
    { label: 'Jeans', value: 'Jeans' },
    { label: 'Skirts', value: 'Skirt' }
];

const Gallery: React.FC<GalleryProps> = ({ onStartSearch }) => {
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [activeCategory, setActiveCategory] = useState<string>('All');

    const fetchProductsData = async (pageNum: number, category?: string, append: boolean = false) => {
        setLoading(true);
        try {
            // Convert 'All' to undefined for API
            const apiCategory = category === 'All' ? undefined : category;
            const data = await getProducts(pageNum, 12, apiCategory);

            if (append) {
                setProducts(prev => [...prev, ...data.products]);
            } else {
                setProducts(data.products);
            }
            setTotalPages(data.pages);
            setTotalItems(data.total);
        } catch (error) {
            console.error('Failed to fetch products', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        setPage(1);
        fetchProductsData(1, activeCategory, false);
    }, [activeCategory]);

    const handleLoadMore = () => {
        const nextPage = page + 1;
        setPage(nextPage);
        fetchProductsData(nextPage, activeCategory, true);
    };

    return (
        <div className="pt-24 pb-12 min-h-screen bg-transparent">
            {/* ... Floating Search Bar & Hero ... */}
            <div className="fixed top-6 left-4 right-4 z-50 flex justify-center">
                <div className="w-full max-w-xl premium-blur bg-white/5 border border-white/10 rounded-full px-6 py-4 flex items-center gap-4 shadow-2xl transition-all focus-within:bg-white/10 focus-within:border-white/20">
                    <SearchIcon className="text-violet-400" size={22} />
                    <input
                        type="text"
                        placeholder="Search for styles, trends..."
                        className="bg-transparent border-none outline-none w-full text-white placeholder-slate-400 font-medium text-lg"
                    />
                </div>
            </div>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8 }}
                className="mb-16 w-full relative"
            >
                <button
                    onClick={onStartSearch}
                    className="w-full min-h-[400px] md:h-[500px] relative overflow-hidden group"
                >
                    {/* Lottie Background Animation */}
                    <div className="absolute inset-0">
                        <Lottie
                            animationData={heroAnimation}
                            loop={true}
                            className="w-full h-full object-cover"
                            rendererSettings={{
                                preserveAspectRatio: 'xMidYMid slice'
                            }}
                        />
                    </div>
                    {/* Overlay for depth and text readability */}
                    <div className="absolute inset-0 bg-gradient-to-r from-black via-black/60 to-transparent backdrop-blur-[2px]" />

                    <div className="relative z-10 max-w-7xl mx-auto px-8 h-full flex flex-col items-start justify-center text-left">
                        <motion.div
                            initial={{ x: -20, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            transition={{ delay: 0.2 }}
                            className="max-w-2xl py-12 px-8 rounded-3xl premium-blur border border-white/10 bg-black/20"
                        >
                            <h2 className="text-5xl md:text-7xl font-black mb-6 tracking-tight text-white leading-[1.1]">
                                Got a Photo?
                                <br />
                                <span className="text-gradient">Find the Look.</span>
                            </h2>

                            <p className="text-xl md:text-2xl font-medium mb-10 text-slate-300 leading-relaxed">
                                Upload any outfit photo and our AI will find the closest
                                <br className="hidden md:block" />
                                matching products in our collection instantly.
                            </p>

                            <div className="btn-primary cursor-pointer w-fit shadow-violet-500/30">
                                <Camera size={24} />
                                <span className="text-lg">Search with Image</span>
                            </div>
                        </motion.div>
                    </div>
                </button>
            </motion.div>

            <div className="max-w-7xl mx-auto px-4">

                {/* Gallery Header */}
                <div className="flex flex-col gap-8 mb-12">
                    <div className="flex justify-between items-end">
                        <div>
                            <h2 className="text-4xl font-black mb-2 flex items-center gap-3">
                                Fresh Arrivals
                                <span className="px-3 py-1 rounded-full bg-violet-500/20 text-violet-400 text-sm font-bold border border-violet-500/30">New</span>
                            </h2>
                            <p className="text-slate-400 text-lg">
                                {loading ? 'Loading...' : `Showing ${totalItems} items`}
                            </p>
                        </div>
                    </div>

                    <div className="flex gap-3 overflow-x-auto pb-4 scrollbar-hide -mx-4 px-4 md:mx-0 md:px-0 mask-gradient-x">
                        {FILTERS.map(filter => (
                            <button
                                key={filter.value}
                                onClick={() => setActiveCategory(filter.value)}
                                className={`relative px-6 py-3 rounded-full text-sm font-bold transition-all whitespace-nowrap z-10 ${activeCategory === filter.value ? 'text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'
                                    }`}
                            >
                                {activeCategory === filter.value && (
                                    <motion.div
                                        layoutId="activeFilter"
                                        className="absolute inset-0 bg-gradient-to-r from-violet-600 to-cyan-600 rounded-full -z-10 shadow-lg shadow-violet-500/25"
                                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                    />
                                )}
                                {filter.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Product Grid */}
                <motion.div
                    className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-8 mb-12"
                    initial="hidden"
                    animate="visible"
                    variants={{
                        visible: { transition: { staggerChildren: 0.05 } }
                    }}
                >
                    {products.map((product, idx) => (
                        <ProductCard key={`${product.id}-${idx}`} product={product} />
                    ))}

                    {loading && [1, 2, 3, 4].map(i => (
                        <div key={`skeleton-${i}`} className="animate-pulse">
                            <div className="bg-slate-200 aspect-[3/4] rounded-2xl mb-4" />
                            <div className="h-4 bg-slate-200 rounded w-3/4 mb-2" />
                            <div className="h-4 bg-slate-200 rounded w-1/4" />
                        </div>
                    ))}
                </motion.div>

                {/* Load More */}
                {!loading && page < totalPages && (
                    <div className="flex justify-center mt-8">
                        <button
                            onClick={handleLoadMore}
                            className="px-8 py-4 rounded-full premium-blur bg-white/5 border border-white/10 font-bold text-white hover:bg-white/10 hover:border-white/20 transition-all flex items-center gap-2 shadow-xl"
                        >
                            Load More <ChevronDown size={20} />
                        </button>
                    </div>
                )}

                {!loading && products.length === 0 && (
                    <div className="text-center py-20 text-slate-400">
                        <p>No products found in this category.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Gallery;
