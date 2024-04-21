package com.example.remorizemobilo;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.util.Log;

public class DataStreamService extends Service {
    private boolean isRunning = false;

    @Override
    public void onCreate() {
        super.onCreate();
        isRunning = true;
        // Start your data streaming here in a separate thread
        new Thread(this::startDataStreaming).start();
    }

    private void startDataStreaming() {
        while (isRunning) {
            // Code to collect data and send it to the server
            sendDataToServer("Sample data chunk");
            try {
                Thread.sleep(1000);  // Adjust the timing based on your needs
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        // If service is killed by system, restart it with the last intent
        return START_REDELIVER_INTENT;
    }

    @Override
    public void onDestroy() {
        isRunning = false;
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;  // We don't provide binding, so return null
    }

    private void sendDataToServer(String data) {
        // Implement network code to send data to server
        Log.i("DataStreamService", "Sending data: " + data);
    }
}
