package mx.vertice.proyectos;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.webkit.URLUtil;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

/** Galería "Vértice · Proyecto del día" empaquetada como app de Android. */
public class MainActivity extends Activity {

    private static final String INICIO = "https://ingmiguelestradaf-rgb.github.io/VERTICE-PROYECTOS/";
    private static final String HOST = "ingmiguelestradaf-rgb.github.io";
    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        web = new WebView(this);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(true);   // pellizcar para hacer zoom en las láminas
        s.setDisplayZoomControls(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                Uri u = req.getUrl();
                String ruta = u.getPath() == null ? "" : u.getPath().toLowerCase();
                if (ruta.endsWith(".zip") || ruta.endsWith(".pdf") || ruta.endsWith(".dxf") || ruta.endsWith(".apk")) {
                    descargar(u.toString());
                    return true;
                }
                if (!HOST.equals(u.getHost())) {   // enlaces externos al navegador
                    startActivity(new Intent(Intent.ACTION_VIEW, u));
                    return true;
                }
                return false;
            }
        });
        web.setDownloadListener((url, ua, disp, mime, len) -> descargar(url));

        if (savedInstanceState != null) {
            web.restoreState(savedInstanceState);
        } else {
            web.loadUrl(INICIO);
        }
    }

    private void descargar(String url) {
        try {
            String nombre = URLUtil.guessFileName(url, null, null);
            DownloadManager.Request r = new DownloadManager.Request(Uri.parse(url));
            r.setTitle(nombre);
            r.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            r.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "Vertice/" + nombre);
            ((DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE)).enqueue(r);
            Toast.makeText(this, "Descargando " + nombre + " en Descargas/Vertice", Toast.LENGTH_SHORT).show();
        } catch (Exception e) {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
