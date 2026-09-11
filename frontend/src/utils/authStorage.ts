/**
 * Token Storage Utility for managing JWT access tokens in localStorage.
 */

const TOKEN_KEY = 'neighbourhood_offers_token';

export const getStoredToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (e) {
    console.error('Error reading token from localStorage', e);
    return null;
  }
};

export const setStoredToken = (token: string): void => {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch (e) {
    console.error('Error saving token to localStorage', e);
  }
};

export const clearStoredToken = (): void => {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch (e) {
    console.error('Error removing token from localStorage', e);
  }
};

export const hasStoredToken = (): boolean => {
  const token = getStoredToken();
  return Boolean(token && token.trim().length > 0);
};
