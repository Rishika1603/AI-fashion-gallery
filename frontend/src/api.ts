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

    // We need blob response for image
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
