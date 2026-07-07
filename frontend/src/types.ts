export interface Product {
    id: string | number;
    name: string;
    style_code: string;
    price_min: number;
    price_max: number;
    image_url: string;
    category: string;
    color_swatches: string[];
    social_label?: string;
    likes: number;
}

export interface SearchResult {
    product: Product;
    match_score: number;
    matched_color: string;
}

export interface PaginatedResponse {
    products: Product[];
    total: number;
    page: number;
    pages: number;
}

export type ScreenState = 'GALLERY' | 'UPLOADING' | 'RESULTS' | 'FASHN_STUDIO';

// ── Fashn.ai Types ──────────────────────────────────────────────────

export interface FashnFeature {
    id: string;
    name: string;
    description: string;
    inputs: string[];
    lifecycle: string;
}

export interface FashnStatusResponse {
    available: boolean;
    features: string[];
}

export interface FashnFeaturesResponse {
    features: FashnFeature[];
    excluded_features: string[];
}
