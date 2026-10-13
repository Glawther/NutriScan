# ProGuard / R8 rules for NutriScan (Android WebView + AndroidX)

# Keep AndroidX WebKit interfaces and JavaScript interface bridges if added
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
-keep class com.glawther.nutriscan.MainActivity$NativeBridge { *; }
-keepclassmembers class com.glawther.nutriscan.MainActivity$NativeBridge {
    public *;
}

# Keep WebChromeClient and WebViewClient subclasses and their methods
-keep public class * extends android.webkit.WebChromeClient {
    public *;
}
-keep public class * extends android.webkit.WebViewClient {
    public *;
}

# Preserve Native and AndroidX Activity Results
-keepclassmembers class androidx.activity.result.** { *; }

# Optimize and remove unused resources
-dontwarn android.webkit.**
-dontwarn androidx.webkit.**
