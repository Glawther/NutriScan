package com.glawther.nutriscan

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.MediaStore
import android.view.View
import android.webkit.*
import android.widget.ProgressBar
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import java.io.File
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var loadingProgressBar: ProgressBar
    private var fileUploadCallback: ValueCallback<Array<Uri>>? = null
    private var cameraPhotoUri: Uri? = null

    // Permission launcher for Camera
    private val requestCameraPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { isGranted ->
            if (!isGranted) {
                Toast.makeText(
                    this,
                    getString(R.string.camera_permission_required),
                    Toast.LENGTH_SHORT
                ).show()
            }
        }

    // Modern ActivityResultLauncher for WebChromeClient.onShowFileChooser
    private val filePickerLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (fileUploadCallback == null) return@registerForActivityResult

            var results: Array<Uri>? = null

            if (result.resultCode == Activity.RESULT_OK) {
                val data = result.data
                if (data?.data != null) {
                    // Chosen single file from Gallery / Documents
                    results = arrayOf(data.data!!)
                } else if (data?.clipData != null) {
                    // Chosen multiple files
                    val clipData = data.clipData!!
                    results = Array(clipData.itemCount) { i -> clipData.getItemAt(i).uri }
                } else if (cameraPhotoUri != null) {
                    // Photo taken with Camera intent
                    results = arrayOf(cameraPhotoUri!!)
                }
            }

            fileUploadCallback?.onReceiveValue(results)
            fileUploadCallback = null
            cameraPhotoUri = null
        }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        setupEdgeToEdge()
        checkCameraPermission()

        webView = findViewById(R.id.webView)
        loadingProgressBar = findViewById(R.id.loadingProgressBar)

        configureWebView()
        setupOnBackPressed()

        webView.loadUrl("file:///android_asset/index.html")
    }

    /**
     * Configures Edge-to-Edge UI & Insets for seamless immersive feel
     */
    private fun setupEdgeToEdge() {
        // Let content render behind system bars with proper insets
        WindowCompat.setDecorFitsSystemWindows(window, false)

        val windowInsetsController = WindowCompat.getInsetsController(window, window.decorView)
        // Set dark status bar & navigation bar icons (false means light text/icons on dark bg)
        windowInsetsController.isAppearanceLightStatusBars = false
        windowInsetsController.isAppearanceLightNavigationBars = false

        val rootContainer = findViewById<View>(R.id.rootContainer)
        ViewCompat.setOnApplyWindowInsetsListener(rootContainer) { view, insets ->
            val statusBarInsets = insets.getInsets(WindowInsetsCompat.Type.statusBars())
            val navBarInsets = insets.getInsets(WindowInsetsCompat.Type.navigationBars())

            // Pad the container to avoid content colliding with status bar and navigation gestures
            view.setPadding(
                statusBarInsets.left.coerceAtLeast(navBarInsets.left),
                statusBarInsets.top,
                statusBarInsets.right.coerceAtLeast(navBarInsets.right),
                navBarInsets.bottom
            )
            insets
        }
    }

    /**
     * Intercepts system back gesture / button using OnBackPressedDispatcher.
     * Allows navigating backward in WebView history before closing the application.
     */
    private fun setupOnBackPressed() {
        val backPressedCallback = object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) {
                    webView.goBack()
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                    isEnabled = true
                }
            }
        }
        onBackPressedDispatcher.addCallback(this, backPressedCallback)
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun configureWebView() {
        val settings = webView.settings

        // Enable JavaScript and modern HTML5 Web Storage
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true

        // File and content access
        settings.allowFileAccess = true
        settings.allowContentAccess = true

        // Responsive viewport and zoom configuration (prevent accidental user scaling)
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true
        settings.setSupportZoom(false)
        settings.builtInZoomControls = false
        settings.displayZoomControls = false

        // Cache mode: fallback to cached data if offline
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        // Media autoplay without gesture
        settings.mediaPlaybackRequiresUserGesture = false

        // Dark background matching Bento canvas #090d16 to prevent white flashing
        webView.setBackgroundColor(Color.parseColor("#090d16"))

        // Register NativeBridge JavaScript Interface
        webView.addJavascriptInterface(NativeBridge(this), "NutriScanNative")

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val url = request?.url?.toString() ?: return false
                if (url.startsWith("file://") || url.startsWith("http://10.0.2.2") || url.startsWith("http://localhost")) {
                    return false
                }
                // External links open in device default browser
                try {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    startActivity(intent)
                } catch (e: Exception) {
                    // Ignore invalid external scheme
                }
                return true
            }

            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                super.onPageStarted(view, url, favicon)
                loadingProgressBar.visibility = View.VISIBLE
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                loadingProgressBar.visibility = View.GONE
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                super.onReceivedError(view, request, error)
                // If main frame fails and not local asset, can show offline message
                if (request?.isForMainFrame == true) {
                    loadingProgressBar.visibility = View.GONE
                }
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                super.onProgressChanged(view, newProgress)
                if (newProgress in 1..99) {
                    loadingProgressBar.visibility = View.VISIBLE
                    loadingProgressBar.progress = newProgress
                } else {
                    loadingProgressBar.visibility = View.GONE
                }
            }

            override fun onShowFileChooser(
                view: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                // Cancel existing pending callback to prevent memory leak or freeze
                fileUploadCallback?.onReceiveValue(null)
                fileUploadCallback = filePathCallback

                // 1. Prepare Camera capture Intent
                val takePictureIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                var photoFile: File? = null
                try {
                    photoFile = createImageFile()
                } catch (ex: IOException) {
                    // File creation failed
                }

                if (photoFile != null) {
                    try {
                        val photoUri = FileProvider.getUriForFile(
                            this@MainActivity,
                            "${applicationContext.packageName}.fileprovider",
                            photoFile
                        )
                        cameraPhotoUri = photoUri
                        takePictureIntent.putExtra(MediaStore.EXTRA_OUTPUT, photoUri)
                    } catch (e: Exception) {
                        cameraPhotoUri = null
                    }
                }

                // 2. Prepare Gallery/File Picker Intent
                val contentSelectionIntent = Intent(Intent.ACTION_GET_CONTENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "image/*"
                }

                // 3. Build Chooser combining Camera and Gallery
                val chooserIntent = Intent(Intent.ACTION_CHOOSER).apply {
                    putExtra(Intent.EXTRA_INTENT, contentSelectionIntent)
                    putExtra(Intent.EXTRA_TITLE, getString(R.string.file_chooser_title))
                    if (cameraPhotoUri != null) {
                        putExtra(Intent.EXTRA_INITIAL_INTENTS, arrayOf(takePictureIntent))
                    }
                }

                return try {
                    filePickerLauncher.launch(chooserIntent)
                    true
                } catch (e: ActivityNotFoundException) {
                    fileUploadCallback?.onReceiveValue(null)
                    fileUploadCallback = null
                    cameraPhotoUri = null
                    Toast.makeText(
                        this@MainActivity,
                        getString(R.string.file_chooser_error),
                        Toast.LENGTH_SHORT
                    ).show()
                    false
                }
            }
        }
    }

    private fun checkCameraPermission() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestCameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    @Throws(IOException::class)
    private fun createImageFile(): File {
        val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val storageDir = getExternalFilesDir(Environment.DIRECTORY_PICTURES)
        return File.createTempFile("NUTRISCAN_${timeStamp}_", ".jpg", storageDir)
    }

    override fun onResume() {
        super.onResume()
        webView.onResume()
    }

    override fun onPause() {
        super.onPause()
        webView.onPause()
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }

    /**
     * Native JavaScript Interface Bridge
     * Exposes native haptic feedback, social sharing, and app environment detection to WebView JavaScript
     */
    class NativeBridge(private val activity: Activity) {

        private val vibrator: Vibrator? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vibratorManager = activity.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager
            vibratorManager?.defaultVibrator ?: (activity.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator)
        } else {
            @Suppress("DEPRECATION")
            activity.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        }

        @JavascriptInterface
        fun vibrate(durationMs: Long) {
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator?.vibrate(
                        VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE)
                    )
                } else {
                    @Suppress("DEPRECATION")
                    vibrator?.vibrate(durationMs)
                }
            } catch (e: Exception) {
                // Ignore vibration failure on devices without vibrator or missing permission
            }
        }

        @JavascriptInterface
        fun shareText(title: String, text: String) {
            activity.runOnUiThread {
                try {
                    val sendIntent = Intent(Intent.ACTION_SEND).apply {
                        type = "text/plain"
                        putExtra(Intent.EXTRA_TEXT, text)
                        if (title.isNotEmpty()) {
                            putExtra(Intent.EXTRA_SUBJECT, title)
                            putExtra(Intent.EXTRA_TITLE, title)
                        }
                    }
                    val chooserIntent = Intent.createChooser(sendIntent, title.ifEmpty { null })
                    activity.startActivity(chooserIntent)
                } catch (e: Exception) {
                    // Ignore share chooser errors
                }
            }
        }

        @JavascriptInterface
        fun isNativeApp(): Boolean {
            return true
        }
    }
}
