"""Internationalization support for MindfulClipboard."""
import json
import locale
import os
from typing import Dict, Optional


class I18n:
    """Handles internationalization for the application."""
    
    def __init__(self, localesDir: str = "locales", defaultLocale: str = "en"):
        self.localesDir = localesDir
        self.defaultLocale = defaultLocale
        self.currentLocale = self._detectSystemLocale()
        self.translations: Dict[str, str] = {}
        self._loadTranslations()
    
    def _detectSystemLocale(self) -> str:
        """Detect system locale and return appropriate language code."""
        try:
            # Get system locale
            systemLocale = locale.getdefaultlocale()[0]
            
            if systemLocale:
                # Extract language code (first 2 characters)
                langCode = systemLocale.split('_')[0].lower()
                
                # Check if we have translations for this language
                localeFile = os.path.join(self.localesDir, f"{langCode}.json")
                if os.path.exists(localeFile):
                    return langCode
        except:
            pass
        
        # Fall back to default locale
        return self.defaultLocale
    
    def _loadTranslations(self) -> None:
        """Load translations for current locale."""
        localeFile = os.path.join(self.localesDir, f"{self.currentLocale}.json")
        
        try:
            with open(localeFile, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Locale file '{localeFile}' not found. Using default locale.")
            
            # Try to load default locale
            defaultFile = os.path.join(self.localesDir, f"{self.defaultLocale}.json")
            try:
                with open(defaultFile, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
                    self.currentLocale = self.defaultLocale
            except FileNotFoundError:
                print(f"Error: Default locale file '{defaultFile}' not found.")
                self.translations = {}
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse locale file '{localeFile}': {e}")
            self.translations = {}
    
    def t(self, key: str, default: Optional[str] = None) -> str:
        """
        Translate a key to the current locale.
        
        Args:
            key: Translation key
            default: Default value if translation not found
        
        Returns:
            Translated string or default value or key itself
        """
        return self.translations.get(key, default or key)
    
    def getLocale(self) -> str:
        """Get current locale code."""
        return self.currentLocale
    
    def setLocale(self, localeCode: str) -> bool:
        """
        Change the current locale.
        
        Args:
            localeCode: Language code (e.g., 'en', 'ar')
        
        Returns:
            True if locale was changed successfully, False otherwise
        """
        localeFile = os.path.join(self.localesDir, f"{localeCode}.json")
        
        if not os.path.exists(localeFile):
            print(f"Warning: Locale file '{localeFile}' not found.")
            return False
        
        self.currentLocale = localeCode
        self._loadTranslations()
        return True
    
    def isRtl(self) -> bool:
        """Check if current locale is right-to-left."""
        rtlLanguages = ['ar', 'he', 'fa', 'ur']
        return self.currentLocale in rtlLanguages


# Global instance
_i18nInstance: Optional[I18n] = None


def initI18n(localesDir: str = "locales", defaultLocale: str = "en") -> I18n:
    """Initialize the i18n system."""
    global _i18nInstance
    _i18nInstance = I18n(localesDir, defaultLocale)
    return _i18nInstance


def getI18n() -> I18n:
    """Get the global i18n instance."""
    global _i18nInstance
    if _i18nInstance is None:
        _i18nInstance = I18n()
    return _i18nInstance


def t(key: str, default: Optional[str] = None) -> str:
    """Shortcut function for translations."""
    return getI18n().t(key, default)