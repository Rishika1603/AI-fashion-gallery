import axios from 'axios';
import type { SearchResult, PaginatedResponse, Product } from './types';

// Set VITE_API_BASE_URL in your deployment environment (e.g. https://api.yourdomain.com/api)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const getProducts = async (page: number = 1, limit: number = 20, category?: string): Promise<PaginatedResponse> => {
    const params: any = { page, limit };
    if (category) params.category = category;
    const response = await axios.get(`${API_BASE_URL}/products`, { params });
    return response.data;
};

export const getProduct = async (id: string | number): Promise<Product> => {
    const response = await axios.get(`${API_BASE_URL}/products/${id}`);
    return response.data;
};

export const searchByPhoto = async (file: File): Promise<SearchResult[]> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${API_BASE_URL}/search-by-photo`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const tryOn = async (userImage: File, garmentUrl: string): Promise<Blob> => {
    const formData = new FormData();
    formData.append('user_image', userImage);
    formData.append('garment_image_url', garmentUrl);
    const response = await axios.post(`${API_BASE_URL}/try-on`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob'
    });
    return response.data;
};

export const chatWithBot = async (message: string, history: { role: string, content: string }[] = []) => {
    const response = await axios.post(`${API_BASE_URL}/chat`, { message, history });
    return response.data;
};

// ── Fashn.ai API Functions ──────────────────────────────────────────

export const getFashnStatus = async () => {
    const response = await axios.get(`${API_BASE_URL}/fashn/status`);
    return response.data;
};

export const getFashnFeatures = async () => {
    const response = await axios.get(`${API_BASE_URL}/fashn/features`);
    return response.data;
};

async function fashnFormPost(endpoint: string, formData: FormData, isVideo: boolean = false) {
    if (isVideo) {
        const response = await axios.post(`${API_BASE_URL}/fashn/${endpoint}`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    }
    const response = await axios.post(`${API_BASE_URL}/fashn/${endpoint}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob'
    });
    return response.data;
}

export const fashnTryOn = async (garmentFile: File, modelFile: File, options?: {
    prompt?: string; resolution?: string; generation_mode?: string;
    num_images?: number; output_format?: string; return_base64?: boolean;
}) => {
    const fd = new FormData();
    fd.append('garment_file', garmentFile);
    fd.append('model_file', modelFile);
    if (options?.prompt) fd.append('prompt', options.prompt);
    if (options?.resolution) fd.append('resolution', options.resolution);
    if (options?.generation_mode) fd.append('generation_mode', options.generation_mode);
    if (options?.num_images) fd.append('num_images', String(options.num_images));
    if (options?.output_format) fd.append('output_format', options.output_format);
    if (options?.return_base64) fd.append('return_base64', 'true');
    return fashnFormPost('tryon', fd);
};

export const fashnProductToModel = async (productFile: File, options?: {
    prompt?: string; faceReferenceFile?: File; aspect_ratio?: string; resolution?: string;
}) => {
    const fd = new FormData();
    fd.append('product_file', productFile);
    if (options?.faceReferenceFile) fd.append('face_reference_file', options.faceReferenceFile);
    if (options?.prompt) fd.append('prompt', options.prompt);
    if (options?.aspect_ratio) fd.append('aspect_ratio', options.aspect_ratio);
    if (options?.resolution) fd.append('resolution', options.resolution);
    return fashnFormPost('product-to-model', fd);
};

export const fashnFaceToModel = async (faceFile: File, options?: {
    prompt?: string; aspect_ratio?: string; resolution?: string;
}) => {
    const fd = new FormData();
    fd.append('face_file', faceFile);
    if (options?.prompt) fd.append('prompt', options.prompt);
    if (options?.aspect_ratio) fd.append('aspect_ratio', options.aspect_ratio);
    if (options?.resolution) fd.append('resolution', options.resolution);
    return fashnFormPost('face-to-model', fd);
};

export const fashnModelCreate = async (imageFile: File, modelName?: string) => {
    const fd = new FormData();
    fd.append('image_file', imageFile);
    if (modelName) fd.append('model_name', modelName);
    const response = await axios.post(`${API_BASE_URL}/fashn/model-create`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const fashnEdit = async (imageFile: File, prompt: string, options?: {
    maskFile?: File; resolution?: string; generation_mode?: string;
}) => {
    const fd = new FormData();
    fd.append('image_file', imageFile);
    fd.append('prompt', prompt);
    if (options?.maskFile) fd.append('mask_file', options.maskFile);
    if (options?.resolution) fd.append('resolution', options.resolution);
    if (options?.generation_mode) fd.append('generation_mode', options.generation_mode);
    return fashnFormPost('edit', fd);
};

export const fashnReframe = async (imageFile: File, aspectRatio: string, options?: {
    resolution?: string;
}) => {
    const fd = new FormData();
    fd.append('image_file', imageFile);
    fd.append('aspect_ratio', aspectRatio);
    if (options?.resolution) fd.append('resolution', options.resolution);
    return fashnFormPost('reframe', fd);
};

export const fashnImageToVideo = async (imageFile: File, options?: {
    prompt?: string; duration?: number; resolution?: string;
}) => {
    const fd = new FormData();
    fd.append('image_file', imageFile);
    if (options?.prompt) fd.append('prompt', options.prompt);
    if (options?.duration) fd.append('duration', String(options.duration));
    if (options?.resolution) fd.append('resolution', options.resolution);
    return fashnFormPost('image-to-video', fd, true);
};

export const fashnBackgroundRemove = async (imageFile: File, returnBase64: boolean = false) => {
    const fd = new FormData();
    fd.append('image_file', imageFile);
    if (returnBase64) fd.append('return_base64', 'true');
    return fashnFormPost('background-remove', fd);
};

// ── Admin-Gated Try-On Request Flow ──────────────────────────────────

export interface TryOnRequestItem {
    id: number;
    session_id: string;
    status: 'pending' | 'approved' | 'completed' | 'rejected';
    admin_note: string | null;
    result_url: string | null;
    created_at: string;
}

export async function submitTryOnRequest(
    sessionId: string,
    personImage: File,
    garmentImage: File,
): Promise<TryOnRequestItem> {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('person_image', personImage);
    formData.append('garment_image', garmentImage);
    const res = await axios.post(`${API_BASE_URL}/tryon/request`, formData);
    return res.data;
}

export async function listTryOnRequests(sessionId: string): Promise<TryOnRequestItem[]> {
    const res = await axios.get(`${API_BASE_URL}/tryon/requests`, {
        params: { session_id: sessionId },
    });
    return res.data;
}

export async function adminGetPendingRequests(adminKey: string): Promise<TryOnRequestItem[]> {
    const res = await axios.get(`${API_BASE_URL}/admin/tryon/pending`, {
        headers: { Authorization: `Bearer ${adminKey}` },
    });
    return res.data;
}

export async function adminGetRequestDetail(adminKey: string, requestId: number): Promise<TryOnRequestItem> {
    const res = await axios.get(`${API_BASE_URL}/admin/tryon/request/${requestId}`, {
        headers: { Authorization: `Bearer ${adminKey}` },
    });
    return res.data;
}

export async function adminApproveTryOn(adminKey: string, requestId: number): Promise<any> {
    const res = await axios.post(`${API_BASE_URL}/admin/tryon/approve/${requestId}`, {}, {
        headers: { Authorization: `Bearer ${adminKey}` },
    });
    return res.data;
}

export async function adminRejectTryOn(adminKey: string, requestId: number, note?: string): Promise<any> {
    const res = await axios.post(`${API_BASE_URL}/admin/tryon/reject/${requestId}`, { note }, {
        headers: { Authorization: `Bearer ${adminKey}` },
    });
    return res.data;
}

export type { FashnFeature, FashnStatusResponse } from './types';