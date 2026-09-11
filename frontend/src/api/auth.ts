import { apiClient } from './client';
import type { AuthToken, User, UserRole } from '../types';

export const authApi = {
  /**
   * Authenticate user with OAuth2 username (email) and password.
   */
  login: async (email: string, password: string): Promise<AuthToken> => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    return apiClient.post<AuthToken>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },

  /**
   * Register a new user account.
   */
  register: async (email: string, password: string, role: UserRole): Promise<User> => {
    return apiClient.post<User>('/auth/register', {
      email,
      password,
      role,
    });
  },

  /**
   * Fetch profile of the currently authenticated user.
   */
  getCurrentUser: async (): Promise<User> => {
    return apiClient.get<User>('/auth/me');
  },
};
