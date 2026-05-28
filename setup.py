#!/usr/bin/env python3
"""
Script qui recrée tout le projet Android et compile l'APK.
Lancé automatiquement par GitHub Actions.
"""
import os, subprocess, sys, stat

def w(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    print(f"✓ {path}")

# ── settings.gradle ──────────────────────────────────────────────────────────
w("settings.gradle", """pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = "BedrockProxy"
include ':app'
""")

# ── build.gradle (root) ───────────────────────────────────────────────────────
w("build.gradle", "plugins { id 'com.android.application' version '8.2.0' apply false }\n")

# ── app/build.gradle ──────────────────────────────────────────────────────────
w("app/build.gradle", """plugins { id 'com.android.application' }
android {
    namespace 'com.bedrockproxy'
    compileSdk 34
    defaultConfig {
        applicationId "com.bedrockproxy"
        minSdk 26; targetSdk 34
        versionCode 1; versionName "1.0"
    }
    buildTypes { release { minifyEnabled false } }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }
    buildFeatures { viewBinding true }
}
dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.11.0'
    implementation 'androidx.constraintlayout:constraintlayout:2.1.4'
}
""")

# ── AndroidManifest.xml ───────────────────────────────────────────────────────
w("app/src/main/AndroidManifest.xml", """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>
    <uses-permission android:name="android.permission.CHANGE_WIFI_MULTICAST_STATE"/>
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/Theme.BedrockProxy">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
        <service android:name=".ProxyService" android:enabled="true"
            android:exported="false" android:foregroundServiceType="dataSync"/>
    </application>
</manifest>
""")

# ── MainActivity.java ─────────────────────────────────────────────────────────
w("app/src/main/java/com/bedrockproxy/MainActivity.java", """package com.bedrockproxy;
import android.content.*;
import android.os.*;
import android.text.*;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import java.net.*;
import java.util.Enumeration;

public class MainActivity extends AppCompatActivity {
    private EditText etServerIp, etServerPort;
    private Button btnToggle;
    private TextView tvStatus, tvLocalIp, tvLog;
    private boolean isRunning = false;
    private SharedPreferences prefs;
    public static final String ACTION_LOG = "com.bedrockproxy.LOG";
    public static final String EXTRA_LOG_MSG = "msg";

    private final BroadcastReceiver logReceiver = new BroadcastReceiver() {
        public void onReceive(Context ctx, Intent i) {
            String msg = i.getStringExtra(EXTRA_LOG_MSG);
            if (msg != null) appendLog(msg);
        }
    };

    @Override protected void onCreate(Bundle s) {
        super.onCreate(s);
        setContentView(R.layout.activity_main);
        prefs = getSharedPreferences("bp", MODE_PRIVATE);
        etServerIp   = findViewById(R.id.etServerIp);
        etServerPort = findViewById(R.id.etServerPort);
        btnToggle    = findViewById(R.id.btnToggle);
        tvStatus     = findViewById(R.id.tvStatus);
        tvLocalIp    = findViewById(R.id.tvLocalIp);
        tvLog        = findViewById(R.id.tvLog);
        etServerIp.setText(prefs.getString("ip",""));
        etServerPort.setText(prefs.getString("port","19132"));
        tvLocalIp.setText("IP locale : " + getLocalIp());
        btnToggle.setOnClickListener(v -> { if (!isRunning) start(); else stop(); });
        etServerIp.addTextChangedListener(new TW(){ public void afterTextChanged(Editable e){ prefs.edit().putString("ip",e.toString()).apply(); }});
        etServerPort.addTextChangedListener(new TW(){ public void afterTextChanged(Editable e){ prefs.edit().putString("port",e.toString()).apply(); }});
    }

    @Override protected void onResume() {
        super.onResume();
        IntentFilter f = new IntentFilter(ACTION_LOG);
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(logReceiver, f, RECEIVER_NOT_EXPORTED);
        else registerReceiver(logReceiver, f);
        isRunning = ProxyService.isRunning(); updateUI();
    }

    @Override protected void onPause() {
        super.onPause();
        try { unregisterReceiver(logReceiver); } catch(Exception e){}
    }

    private void start() {
        String ip = etServerIp.getText().toString().trim();
        String ps = etServerPort.getText().toString().trim();
        if (ip.isEmpty()) { etServerIp.setError("IP requise"); return; }
        int port; try { port = Integer.parseInt(ps); } catch(Exception e){ etServerPort.setError("Port invalide"); return; }
        tvLog.setText("");
        Intent i = new Intent(this, ProxyService.class);
        i.setAction(ProxyService.ACTION_START);
        i.putExtra(ProxyService.EXTRA_IP, ip);
        i.putExtra(ProxyService.EXTRA_PORT, port);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(i); else startService(i);
        isRunning = true; updateUI();
    }

    private void stop() {
        Intent i = new Intent(this, ProxyService.class);
        i.setAction(ProxyService.ACTION_STOP);
        startService(i);
        isRunning = false; updateUI(); appendLog("Proxy arrêté.");
    }

    private void updateUI() {
        if (isRunning) {
            btnToggle.setText("ARRÊTER");
            btnToggle.setBackgroundTintList(ContextCompat.getColorStateList(this, R.color.red));
            tvStatus.setText("Proxy actif ✅");
            tvStatus.setTextColor(0xFF4ADE80);
        } else {
            btnToggle.setText("LANCER");
            btnToggle.setBackgroundTintList(ContextCompat.getColorStateList(this, R.color.accent));
            tvStatus.setText("Inactif");
            tvStatus.setTextColor(0xFF6B6B80);
        }
        etServerIp.setEnabled(!isRunning);
        etServerPort.setEnabled(!isRunning);
    }

    private void appendLog(String msg) {
        runOnUiThread(() -> {
            String cur = tvLog.getText().toString();
            tvLog.setText(cur.isEmpty() ? msg : cur + "\\n" + msg);
        });
    }

    private String getLocalIp() {
        try {
            Enumeration<NetworkInterface> ifaces = NetworkInterface.getNetworkInterfaces();
            while (ifaces.hasMoreElements()) {
                NetworkInterface iface = ifaces.nextElement();
                if (iface.isLoopback() || !iface.isUp()) continue;
                Enumeration<InetAddress> addrs = iface.getInetAddresses();
                while (addrs.hasMoreElements()) {
                    InetAddress a = addrs.nextElement();
                    if (!a.isLoopbackAddress() && a.getHostAddress().contains(".")) return a.getHostAddress();
                }
            }
        } catch(Exception e){}
        return "inconnue";
    }

    abstract static class TW implements TextWatcher {
        public void beforeTextChanged(CharSequence s,int a,int b,int c){}
        public void onTextChanged(CharSequence s,int a,int b,int c){}
    }
}
""")

# ── ProxyService.java ─────────────────────────────────────────────────────────
w("app/src/main/java/com/bedrockproxy/ProxyService.java", """package com.bedrockproxy;
import android.app.*;
import android.content.Intent;
import android.os.IBinder;
import android.util.Log;
import androidx.core.app.NotificationCompat;
import java.net.*;
import java.nio.*;
import java.nio.ByteOrder;
import java.util.Arrays;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

public class ProxyService extends Service {
    private static final String CH = "proxy_ch";
    private static final int NID = 1;
    public static final String ACTION_START = "START";
    public static final String ACTION_STOP  = "STOP";
    public static final String EXTRA_IP   = "ip";
    public static final String EXTRA_PORT = "port";

    private static final byte PONG = 0x1C;
    private static final byte[] MAGIC = {0x00,(byte)0xFF,(byte)0xFF,0x00,(byte)0xFE,(byte)0xFE,(byte)0xFE,(byte)0xFE,(byte)0xFD,(byte)0xFD,(byte)0xFD,(byte)0xFD,0x12,0x34,0x56,0x78};

    private static volatile boolean running = false;
    private ExecutorService exec;
    private final AtomicBoolean stop = new AtomicBoolean(false);
    private String remoteIp; private int remotePort;
    private DatagramSocket proxySock, lanSock;

    public static boolean isRunning(){ return running; }
    public IBinder onBind(Intent i){ return null; }

    public void onCreate(){
        super.onCreate(); exec = Executors.newCachedThreadPool();
        NotificationChannel ch = new NotificationChannel(CH,"Proxy",NotificationManager.IMPORTANCE_LOW);
        getSystemService(NotificationManager.class).createNotificationChannel(ch);
    }

    public int onStartCommand(Intent i, int f, int id){
        if(i==null) return START_NOT_STICKY;
        if(ACTION_STOP.equals(i.getAction())){ doStop(); stopSelf(); return START_NOT_STICKY; }
        if(ACTION_START.equals(i.getAction())){
            remoteIp = i.getStringExtra(EXTRA_IP);
            remotePort = i.getIntExtra(EXTRA_PORT, 19132);
            startForeground(NID, new NotificationCompat.Builder(this,CH)
                .setContentTitle("BedrockProxy").setContentText(remoteIp+":"+remotePort)
                .setSmallIcon(android.R.drawable.ic_media_play).setOngoing(true).build());
            stop.set(false); running = true;
            exec.submit(this::runProxy);
            exec.submit(this::runBroadcast);
        }
        return START_STICKY;
    }

    public void onDestroy(){ doStop(); exec.shutdownNow(); super.onDestroy(); }

    private void runProxy(){
        log("Résolution de "+remoteIp+"...");
        InetAddress remote;
        try { remote = InetAddress.getByName(remoteIp); log("OK : "+remote.getHostAddress()); }
        catch(Exception e){ log("Erreur DNS : "+e.getMessage()); stopSelf(); return; }
        try {
            proxySock = new DatagramSocket(19132);
            proxySock.setBroadcast(true); proxySock.setSoTimeout(1000);
            log("En écoute port 19132 UDP");
            log("Ouvre Minecraft → Amis → LAN");
        } catch(Exception e){ log("Erreur socket : "+e.getMessage()); stopSelf(); return; }

        byte[] buf = new byte[2048];
        InetAddress consoleAddr = null; int consolePort = -1;

        while(!stop.get()){
            try {
                DatagramPacket pkt = new DatagramPacket(buf, buf.length);
                try { proxySock.receive(pkt); } catch(SocketTimeoutException e){ continue; }
                byte[] data = Arrays.copyOf(pkt.getData(), pkt.getLength());
                boolean fromRemote = pkt.getAddress().equals(remote);
                if(!fromRemote){
                    consoleAddr = pkt.getAddress(); consolePort = pkt.getPort();
                    proxySock.send(new DatagramPacket(data, data.length, remote, remotePort));
                } else if(consoleAddr != null){
                    proxySock.send(new DatagramPacket(data, data.length, consoleAddr, consolePort));
                }
            } catch(Exception e){ if(!stop.get()) log("Erreur : "+e.getMessage()); }
        }
        try{ proxySock.close(); }catch(Exception e){}
    }

    private void runBroadcast(){
        try {
            lanSock = new DatagramSocket();
            lanSock.setBroadcast(true);
            InetAddress bc = InetAddress.getByName("255.255.255.255");
            long guid = System.currentTimeMillis();
            String motd = "MCPE;BedrockProxy;800;1.21.0;0;20;"+guid+";Proxy;Survival;1;19132;19133;";
            while(!stop.get()){
                byte[] mb = motd.getBytes();
                ByteBuffer b = ByteBuffer.allocate(1+8+8+16+2+mb.length).order(ByteOrder.BIG_ENDIAN);
                b.put(PONG); b.putLong(System.currentTimeMillis()); b.putLong(guid);
                b.put(MAGIC); b.putShort((short)mb.length); b.put(mb);
                lanSock.send(new DatagramPacket(b.array(), b.array().length, bc, 19132));
                Thread.sleep(1500);
            }
        } catch(Exception e){ if(!stop.get()) log("Broadcast : "+e.getMessage()); }
        finally { try{ lanSock.close(); }catch(Exception e){} }
    }

    private void doStop(){ stop.set(true); running=false; try{if(proxySock!=null)proxySock.close();}catch(Exception e){} try{if(lanSock!=null)lanSock.close();}catch(Exception e){} }
    private void log(String m){ Log.d("BP",m); Intent i=new Intent(MainActivity.ACTION_LOG); i.putExtra(MainActivity.EXTRA_LOG_MSG,m); sendBroadcast(i); }
}
""")

# ── Layouts & Resources ───────────────────────────────────────────────────────
w("app/src/main/res/layout/activity_main.xml", """<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent" android:layout_height="match_parent"
    android:background="#0A0A0F" android:fillViewport="true">
  <LinearLayout android:layout_width="match_parent" android:layout_height="wrap_content"
      android:orientation="vertical" android:padding="20dp">

    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="BedrockProxy" android:textSize="24sp" android:textStyle="bold"
        android:textColor="#E8E8F0" android:layout_marginBottom="4dp"/>
    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="Minecraft Bedrock LAN Proxy" android:textSize="12sp"
        android:textColor="#6B6B80" android:layout_marginBottom="24dp"/>

    <TextView android:id="@+id/tvStatus" android:layout_width="match_parent"
        android:layout_height="wrap_content" android:text="Inactif"
        android:textSize="14sp" android:textColor="#6B6B80" android:gravity="center"
        android:padding="12dp" android:background="#111118" android:layout_marginBottom="8dp"/>

    <TextView android:id="@+id/tvLocalIp" android:layout_width="match_parent"
        android:layout_height="wrap_content" android:text="IP locale : ..."
        android:textSize="12sp" android:textColor="#6B6B80" android:gravity="center"
        android:fontFamily="monospace" android:layout_marginBottom="24dp"/>

    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="IP / Domaine du serveur" android:textSize="11sp"
        android:textColor="#6B6B80" android:layout_marginBottom="6dp"/>
    <EditText android:id="@+id/etServerIp" android:layout_width="match_parent"
        android:layout_height="wrap_content" android:hint="ex: play.monserveur.net"
        android:textColor="#E8E8F0" android:textColorHint="#3A3A50"
        android:textSize="15sp" android:padding="12dp" android:inputType="text"
        android:singleLine="true" android:background="#1A1A24" android:layout_marginBottom="14dp"/>

    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="Port" android:textSize="11sp"
        android:textColor="#6B6B80" android:layout_marginBottom="6dp"/>
    <EditText android:id="@+id/etServerPort" android:layout_width="match_parent"
        android:layout_height="wrap_content" android:hint="19132"
        android:textColor="#E8E8F0" android:textColorHint="#3A3A50"
        android:textSize="15sp" android:padding="12dp" android:inputType="number"
        android:singleLine="true" android:background="#1A1A24" android:layout_marginBottom="28dp"/>

    <Button android:id="@+id/btnToggle" android:layout_width="match_parent"
        android:layout_height="56dp" android:text="LANCER" android:textSize="15sp"
        android:textStyle="bold" android:textColor="#FFFFFF"
        android:backgroundTint="#7C6FFF" android:layout_marginBottom="24dp"
        android:stateListAnimator="@null"/>

    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="Mode d&#39;emploi" android:textSize="11sp" android:textColor="#7C6FFF"
        android:layout_marginBottom="8dp"/>
    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="1. Entre IP + port\\n2. Appuie LANCER\\n3. Minecraft → Amis → LAN\\n4. Rejoins BedrockProxy"
        android:textSize="13sp" android:textColor="#A0A0B8" android:lineSpacingExtra="4dp"
        android:background="#111118" android:padding="14dp" android:layout_marginBottom="14dp"/>

    <TextView android:id="@+id/tvLog" android:layout_width="match_parent"
        android:layout_height="wrap_content" android:text=""
        android:hint="Logs..." android:textColorHint="#3A3A50"
        android:textSize="12sp" android:textColor="#A0A0B8"
        android:fontFamily="monospace" android:lineSpacingExtra="3dp"
        android:background="#111118" android:padding="14dp"/>

  </LinearLayout>
</ScrollView>
""")

w("app/src/main/res/values/strings.xml", '<?xml version="1.0" encoding="utf-8"?>\n<resources><string name="app_name">BedrockProxy</string></resources>\n')
w("app/src/main/res/values/colors.xml", '<?xml version="1.0" encoding="utf-8"?>\n<resources><color name="accent">#7C6FFF</color><color name="red">#FF4444</color></resources>\n')
w("app/src/main/res/values/themes.xml", """<?xml version="1.0" encoding="utf-8"?>
<resources>
  <style name="Theme.BedrockProxy" parent="Theme.MaterialComponents.DayNight.NoActionBar">
    <item name="colorPrimary">#7C6FFF</item>
    <item name="android:windowBackground">#0A0A0F</item>
    <item name="android:statusBarColor">#0A0A0F</item>
  </style>
</resources>
""")

# Minimal mipmap launcher icon (1x1 PNG in base64)
import base64
png_b64 = (
    "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz"
    "AAALEgAACxIB0t1+/AAAABx0RVh0U29mdHdhcmUAQWRvYmUgRmlyZXdvcmtzIENTNXG14zYAAAAW"
    "SURBVGje7cEBDQAAAMKg909tDjehAAAAAAAAAADgbgIMAAABEqrwAAAAAElFTkSuQmCC"
)
for dpi in ["mdpi","hdpi","xhdpi","xxhdpi","xxxhdpi"]:
    path = f"app/src/main/res/mipmap-{dpi}/ic_launcher.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(base64.b64decode(png_b64))
    print(f"✓ {path}")

print("\n✅ Tous les fichiers créés !")
print("Lancement de Gradle wrapper...")

# Generate gradlew via gradle wrapper task
r = subprocess.run(["gradle", "wrapper", "--gradle-version", "8.2"], capture_output=True, text=True)
print(r.stdout); print(r.stderr)

if os.path.exists("gradlew"):
    os.chmod("gradlew", os.stat("gradlew").st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print("✓ gradlew généré")
    r2 = subprocess.run(["./gradlew", "assembleDebug", "--stacktrace"], capture_output=True, text=True)
    print(r2.stdout[-3000:] if len(r2.stdout)>3000 else r2.stdout)
    if r2.returncode == 0:
        print("\n🎉 APK compilé avec succès !")
    else:
        print(r2.stderr[-2000:] if len(r2.stderr)>2000 else r2.stderr)
        sys.exit(1)
else:
    print("❌ gradlew pas généré, essai fallback...")
    sys.exit(1)
