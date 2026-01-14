import { useState, useEffect } from 'react';

// This custom hook manages the application's theme (light or dark mode).
export const useTheme = () => {
  // Initialize state from localStorage or system preference.
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Check if window is defined (to avoid SSR errors).
    if (typeof window === 'undefined') {
      return false;
    }
    try {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme) {
        return savedTheme === 'dark';
      }
      // If no theme is saved, use the user's system preference.
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    } catch (e) {
      // If localStorage is disabled, default to light mode.
      console.error("Failed to access localStorage for theme:", e);
      return false;
    }
  });

  // Effect to apply the theme and save it to localStorage.
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    try {
      localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
    } catch (e) {
      console.error("Failed to save theme to localStorage:", e);
    }
  }, [isDarkMode]);

  // Return the theme state and a function to toggle it.
  return { isDarkMode, setIsDarkMode };
};