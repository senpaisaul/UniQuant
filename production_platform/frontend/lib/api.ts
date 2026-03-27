import axios from 'axios';

// Create axios instance with base URL pointing to the backend
// In Docker, this will be handled by networking, but for client-side calls
// we typically proxy or use the exposed URL.
const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
});

export default api;
