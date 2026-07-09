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

// ── Try-On Request types ──────────────────────────────────────────────────

export interface TryOnRequestItem {
    id: number;
    session_id: string;
    status: 'pending' | 'approved' | 'rejected' | 'completed';
    garment_url?: string;
    user_photo_url?: string;
    result_url?: string;
    admin_note?: string;
    created_at: string;
    has_images?: boolean;
    request_type?: 'access' | 'tryon';
}

// ── Try-On Access Request (gate before upload) ─────────────────────

export const requestTryOnAccess = async (sessionId: string): Promise<{ id: number; status: string; message: string }> => {
    const response = await axios.post(`${API_BASE_URL}/tryon/request-access`, { session_id: sessionId });
    return response.data;
};

export const checkTryOnAccess = async (sessionId: string): Promise<{ status: string; request_id?: number; admin_note?: string }> => {
    const response = await axios.get(`${API_BASE_URL}/tryon/access-status`, { params: { session_id: sessionId } });
    return response.data;
};

// ── Try-On Request API (admin-gated workflow) ─────────────────────────────

export const submitTryOnRequest = async (
    sessionId: string,
    userPhoto: File,
    garmentPhoto: File
): Promise<void> => {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('user_photo', userPhoto);
    formData.append('garment_photo', garmentPhoto);
    await axios.post(`${API_BASE_URL}/try-on-requests`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
};

export const listTryOnRequests = async (sessionId: string): Promise<TryOnRequestItem[]> => {
    const response = await axios.get(`${API_BASE_URL}/try-on-requests`, {
        params: { session_id: sessionId },
    });
    return response.data;
};

// ── Admin API ─────────────────────────────────────────────────────────────

export const adminGetPendingRequests = async (adminKey: string): Promise<TryOnRequestItem[]> => {
    const response = await axios.get(`${API_BASE_URL}/admin/try-on-requests/pending`, {
        headers: { 'X-Admin-Key': adminKey },
    });
    return response.data;
};

export const adminApproveTryOn = async (adminKey: string, requestId: number): Promise<void> => {
    await axios.post(
        `${API_BASE_URL}/admin/try-on-requests/${requestId}/approve`,
        {},
        { headers: { 'X-Admin-Key': adminKey } }
    );
};

export const adminRejectTryOn = async (adminKey: string, requestId: number, note?: string): Promise<void> => {
    await axios.post(
        `${API_BASE_URL}/admin/try-on-requests/${requestId}/reject`,
        { note },
        { headers: { 'X-Admin-Key': adminKey } }
    );
};

// ── Admin Settings / Credentials Manager ───────────────────────────────────

export interface SettingItem {
    key: string;
    category: string;
    label: string;
    description: string;
    sensitive: boolean;
    value: string | null;
    has_value: boolean;
}

export interface SettingsResponse {
    settings: SettingItem[];
}

export const getAdminSettings = async (adminKey: string): Promise<SettingsResponse> => {
    const response = await axios.get(`${API_BASE_URL}/admin/settings`, {
        headers: { 'X-Admin-Key': adminKey },
    });
    return response.data;
};

export const updateAdminSettings = async (
    adminKey: string,
    settings: Record<string, string>
): Promise<{ updated: string[]; message: string }> => {
    const response = await axios.put(
        `${API_BASE_URL}/admin/settings`,
        { settings },
        { headers: { 'X-Admin-Key': adminKey } }
    );
    return response.data;
};

// ── Fashn.ai API stubs ────────────────────────────────────────────────────
// These proxy to the backend which forwards to Fashn.ai's external service.
// The backend must have FASHN_API_KEY configured and matching routes.

interface FashnStatus {
    available: boolean;
    message?: string;
}

export const getFashnStatus = async (): Promise<FashnStatus> => {
    const response = await axios.get(`${API_BASE_URL}/fashn/status`);
    return response.data;
};

export const fashnTryOn = async (
    garmentImage: File,
    modelImage: File,
    options?: { prompt?: string; resolution?: string; generation_mode?: string; num_images?: number }
): Promise<Blob> => {
    const formData = new FormData();
    formData.append('garment_image', garmentImage);
    formData.append('model_image', modelImage);
    if (options?.prompt) formData.append('prompt', options.prompt);
    if (options?.resolution) formData.append('resolution', options.resolution);
    if (options?.generation_mode) formData.append('generation_mode', options.generation_mode);
    if (options?.num_images) formData.append('num_images', String(options.num_images));
    const response = await axios.post(`${API_BASE_URL}/fashn/try-on`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
    });
    return response.data;
};

export const fashnProductToModel = async (
    productImage: File,
    options?: { prompt?: string; faceReferenceFile?: File; aspect_ratio?: string; resolution?: string }
): Promise<Blob> => {
    const formData = new FormData();
    formData.append('product_image', productImage);
    if (options?.prompt) formData.append('prompt', options.prompt);
    if (options?.faceReferenceFile) formData.append('face_reference', options.faceReferenceFile);
    if (options?.aspect_ratio) formData.append('aspect_ratio', options.aspect_ratio);
    if (options?.resolution) formData.append('resolution', options.resolution);
    const response = await axios.post(`${API_BASE_URL}/fashn/product-to-model`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
    });
    return response.data;
};

export const fashnFaceToModel = async (
    faceImage: File,
    options?: { prompt?: string; aspect_ratio?: string; resolution?: string }
): Promise<Blob> => {
    const formData = new FormData();
    formData.append('face_image', faceImage);
    if (options?.prompt) formData.append('prompt', options.prompt);
    if (options?.aspect_ratio) formData.append('aspect_ratio', options.aspect_ratio);
    if (options?.resolution) formData.append('resolution', options.resolution);
    const response = await axios.post(`${API_BASE_URL}/fashn/face-to-model`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
    });
    return response.data;
};

export const fashnModelCreate = async (
    modelImage: File,
    modelName?: string
): Promise<{ prediction_id: string; status: string }> => {
    const formData = new FormData();
    formData.append('model_image', modelImage);
    if (modelName) formData.append('model_name', modelName);
    const response = await axios.post(`${API_BASE_URL}/fashn/model-create`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const fashnEdit = async (
    image: File,
    prompt: string,
    options?: { maskFile?: File; resolution?: string; generation_mode?: string }
): Promise<Blob> => {
    const formData = new FormData();
    formData.append('image', image);
    formData.append('prompt', prompt);
    if (options?.maskFile) formData.append('mask', options.maskFile);
    if (options?.resolution) formData.append('resolution', options.resolution);
    if (options?.generation_mode) formData.append('generation_mode', options.generation_mode);
    const response = await axios.post(`${API_BASE_URL}/fashn/edit`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
    });
    return response.data;
};

export const fashnReframe = async (
    image: File,
    aspectRatio: string,
    options?: { resolution?: string }
): Promise<Blob> => {
    const formData = new FormData();
    formData.append('image', image);
    formData.append('aspect_ratio', aspectRatio);
    if (options?.resolution) formData.append('resolution', options.resolution);
    const response = await axios.post(`${API_BASE_URL}/fashn/reframe`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
    });
    return response.data;
};

export const fashnImageToVideo = async (
    image: File,
    options?: { prompt?: string; duration?: number; resolution?: string }
): Promise<{ video_url: string }> => {
    const formData = new FormData();
    formData.append('image', image);
    if (options?.prompt) formData.append('prompt', options.prompt);
    if (options?.duration) formData.append('duration', String(options.duration));
    if (options?.resolution) formData.append('resolution', options.resolution);
    const response = await axios.post(`${API_BASE_URL}/fashn/image-to-video`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const fashnBackgroundRemove = async (image: File): Promise<Blob> => {
    const formData = new FormData();
    formData.append('image', image);
    const response = await axios.post(`${API_BASE_URL}/fashn/background-remove`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
    });
    return response.data;
};
