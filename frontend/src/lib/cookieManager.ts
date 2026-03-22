import Cookies from 'js-cookie';

const COOKIE_KEYS = {
  USER: 'boneage_user',
  TOKEN: 'boneage_token',
  CONSENT: 'boneage_consent',
  PREFERENCES: 'boneage_preferences'
};

const COOKIE_OPTIONS = {
  expires: 30,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  path: '/'
};

export const CookieManager = {
  set: (key: string, value: any, options = COOKIE_OPTIONS) => {
    try {
      const stringValue = typeof value === 'string' ? value : JSON.stringify(value);
      Cookies.set(key, stringValue, options);
    } catch (error) {
      console.error('Failed to set cookie:', error);
    }
  },

  get: (key: string): string | null => {
    try {
      return Cookies.get(key) || null;
    } catch (error) {
      console.error('Failed to get cookie:', error);
      return null;
    }
  },

  getJSON: (key: string): any | null => {
    try {
      const value = Cookies.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      console.error('Failed to parse cookie JSON:', error);
      return null;
    }
  },

  remove: (key: string) => {
    try {
      Cookies.remove(key, { path: '/' });
    } catch (error) {
      console.error('Failed to remove cookie:', error);
    }
  },

  removeAll: () => {
    Object.values(COOKIE_KEYS).forEach(key => {
      CookieManager.remove(key);
    });
  }
};

export const AuthCookie = {
  setUser: (user: any) => {
    CookieManager.set(COOKIE_KEYS.USER, user);
  },

  getUser: () => {
    return CookieManager.getJSON(COOKIE_KEYS.USER);
  },

  setToken: (token: string) => {
    CookieManager.set(COOKIE_KEYS.TOKEN, token);
  },

  getToken: () => {
    return CookieManager.get(COOKIE_KEYS.TOKEN);
  },

  clearAuth: () => {
    CookieManager.remove(COOKIE_KEYS.USER);
    CookieManager.remove(COOKIE_KEYS.TOKEN);
  }
};

export const ConsentCookie = {
  setConsent: (consented: boolean) => {
    const consentData = {
      consented,
      timestamp: new Date().toISOString(),
      version: '1.0'
    };
    CookieManager.set(COOKIE_KEYS.CONSENT, consentData, {
      ...COOKIE_OPTIONS,
      expires: 365
    });
  },

  getConsent: () => {
    return CookieManager.getJSON(COOKIE_KEYS.CONSENT);
  },

  hasConsented: () => {
    const consent = ConsentCookie.getConsent();
    return consent?.consented === true;
  }
};

export const PreferencesCookie = {
  setPreferences: (preferences: Record<string, any>) => {
    CookieManager.set(COOKIE_KEYS.PREFERENCES, preferences);
  },

  getPreferences: () => {
    return CookieManager.getJSON(COOKIE_KEYS.PREFERENCES) || {};
  },

  updatePreference: (key: string, value: any) => {
    const current = PreferencesCookie.getPreferences();
    PreferencesCookie.setPreferences({ ...current, [key]: value });
  }
};

export default CookieManager;