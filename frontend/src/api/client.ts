/**
 * Centralized HTTP API Client for Neighbourhood Offers.
 */

import { clearStoredToken, getStoredToken } from '../utils/authStorage';

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000'
).replace(/\/+$/, '');

export class ApiClientError extends Error {
  status: number;
  detail?: any;

  constructor(status: number, message: string, detail?: any) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: any;
  params?: Record<string, string | number | boolean | undefined | null>;
}

const getErrorMessageForStatus = (status: number, detail?: any): string => {
  if (typeof detail === 'string' && detail.trim().length > 0) {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    // FastAPI validation errors (422)
    return detail.map((err) => `${err.loc?.slice(-1)[0] || 'field'}: ${err.msg}`).join(', ');
  }

  switch (status) {
    case 400:
      return 'Bad request. Please verify your input.';
    case 401:
      return 'Your session has expired. Please log in again.';
    case 403:
      return "You don't have permission to perform this action.";
    case 404:
      return 'The requested resource was not found.';
    case 409:
      return 'Conflict: That action could not be completed because the resource has changed.';
    case 422:
      return 'Please check the information you entered.';
    case 500:
    case 502:
    case 503:
      return 'A server error occurred. Please try again later.';
    default:
      return `Request failed with status ${status}.`;
  }
};

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { body, params, headers: customHeaders, ...customOptions } = options;

  // Build Query String if params provided
  let url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        searchParams.append(key, String(val));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
  }

  const headers = new Headers(customHeaders);

  // Attach token if available
  const token = getStoredToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Handle body & Content-Type
  let serializedBody: any = undefined;
  if (body !== undefined) {
    if (body instanceof FormData || body instanceof URLSearchParams) {
      serializedBody = body;
    } else {
      if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
      }
      serializedBody = JSON.stringify(body);
    }
  }

  try {
    const response = await fetch(url, {
      ...customOptions,
      headers,
      body: serializedBody,
    });

    // Handle 401 Unauthorized
    if (response.status === 401) {
      clearStoredToken();
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }

    // Parse response body if present
    const contentType = response.headers.get('content-type');
    const isJson = contentType && contentType.includes('application/json');
    const data = isJson ? await response.json().catch(() => null) : await response.text().catch(() => null);

    if (!response.ok) {
      const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : data;
      const message = getErrorMessageForStatus(response.status, detail);
      throw new ApiClientError(response.status, message, detail);
    }

    return data as T;
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    // Network errors, connection refused, CORS failure, etc.
    const networkMessage = (error as Error)?.message || 'Unable to connect to the server.';
    throw new ApiClientError(0, networkMessage);
  }
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'POST', body }),

  put: <T>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'PUT', body }),

  patch: <T>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'PATCH', body }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'DELETE' }),
};
