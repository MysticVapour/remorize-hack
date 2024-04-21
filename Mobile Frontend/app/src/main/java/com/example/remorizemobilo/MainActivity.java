package com.example.remorizemobilo;

import org.json.JSONException;
import org.json.JSONObject;
import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import java.io.IOException;
import java.text.BreakIterator;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.Locale;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.Response;

public class MainActivity extends AppCompatActivity {
    private static final int REQUEST_RECORD_AUDIO_PERMISSION_CODE = 1;
    private SpeechRecognizer speechRecognizer;
    private TextView statusTextView;
    private Button stopButton;
    private Button resumeButton;
    TextView notesTextView;
    private Handler handler = new Handler();
    private Runnable periodicListener;
    private String userEmail;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        SharedPreferences prefs = getSharedPreferences("AppPrefs", MODE_PRIVATE);
        String userEmail = prefs.getString("userEmail", null);
        String userUUID = prefs.getString("userUUID", null);

        Intent intent = getIntent();
        userEmail = intent.getStringExtra("email");

        notesTextView = findViewById(R.id.notesTextView);
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
        statusTextView = findViewById(R.id.statusTextView);
        stopButton = findViewById(R.id.stopButton);
        resumeButton = findViewById(R.id.resumeButton);

        stopButton.setOnClickListener(v -> {
            stopListening();
            statusTextView.setText("Not listening to you anymore...");
            stopButton.setVisibility(View.GONE);
            resumeButton.setVisibility(View.VISIBLE);
        });

        resumeButton.setOnClickListener(v -> {
            startListening();
            statusTextView.setText("Noting down your thoughts...");
            stopButton.setVisibility(View.VISIBLE);
            resumeButton.setVisibility(View.GONE);
        });

        if (!isMicrophonePermissionGranted()) {
            requestMicrophonePermission();
        } else {
            startListening();
        }
    }

    private void startListening() {
        periodicListener = new Runnable() {
            @Override
            public void run() {
                if (speechRecognizer != null) {
                    speechRecognizer.destroy();
                }
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(MainActivity.this);
                setRecognizerIntent();
            }
        };
        handler.post(periodicListener);
    }

    private void stopListening() {
        if (speechRecognizer != null) {
            speechRecognizer.stopListening();
            speechRecognizer.cancel();
            speechRecognizer.destroy();
            speechRecognizer = null;
        }
        handler.removeCallbacks(periodicListener);
    }

    private void setRecognizerIntent() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault());
        intent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, this.getPackageName());
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5);

        speechRecognizer.setRecognitionListener(new RecognitionListener() {
            @Override
            public void onResults(Bundle results) {
                ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                if (matches != null && !matches.isEmpty()) {
                    sendTextToServer(matches.get(0));

                }
                handler.postDelayed(periodicListener, 1); // Schedule next listening
            }

            @Override
            public void onReadyForSpeech(Bundle params) {
                statusTextView.setText("Noting down your thoughts...");
            }

            @Override
            public void onBeginningOfSpeech() {}

            @Override
            public void onRmsChanged(float rmsdB) {}

            @Override
            public void onBufferReceived(byte[] buffer) {}

            @Override
            public void onEndOfSpeech() {}

            @Override
            public void onError(int error) {
                handler.postDelayed(periodicListener, 1); // Restart on error
            }

            @Override
            public void onPartialResults(Bundle partialResults) {}

            @Override
            public void onEvent(int eventType, Bundle params) {}
        });

        speechRecognizer.startListening(intent);
    }

    private void sendTextToServer(String text) {
        try {
            JSONObject obj = new JSONObject(text);
            getRelevantNotes(obj.getString("data"));
        } catch (JSONException e) {
            System.err.println(e);
        }
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyyMMddHH'00'");
        String dateTime = dateFormat.format(new Date());
        String userUUID = getSharedPreferences("AppPrefs", MODE_PRIVATE).getString("userUUID", "");

        OkHttpClient client = new OkHttpClient();
        MediaType JSON = MediaType.parse("application/json; charset=utf-8");
        String json = "{\"uuid\":\"" + userUUID + "\", \"dateTime\":\"" + dateTime + "\", \"text\":\"" + text + "\"}";
        RequestBody body = RequestBody.create(json, JSON);
        Request request = new Request.Builder()
                .url("https://7508-129-2-192-158.ngrok-free.app/receive_text")
                .post(body)
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onResponse(@NonNull Call call, @NonNull Response response) throws IOException {
                runOnUiThread(() -> Toast.makeText(MainActivity.this, "Text sent successfully", Toast.LENGTH_SHORT).show());
            }

            @Override
            public void onFailure(@NonNull Call call, @NonNull IOException e) {
                runOnUiThread(() -> Toast.makeText(MainActivity.this, "Failed to send text: " + e.getMessage(), Toast.LENGTH_LONG).show());
            }
        });
    }

    private void getRelevantNotes(String query) {
        OkHttpClient client = new OkHttpClient();
        MediaType JSON = MediaType.parse("application/json; charset=utf-8");
        String json = "{\"query\":\"" + query + "\"}";
        RequestBody body = RequestBody.create(json, JSON);
        Request request = new Request.Builder()
                .url("https://7508-129-2-192-158.ngrok-free.app/get_relevant_notes")
                .post(body)
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onResponse(@NonNull Call call, @NonNull Response response) throws IOException {
                String responseBody = response.body().string();
                runOnUiThread(() -> updateTextView(responseBody));
            }

            @Override
            public void onFailure(@NonNull Call call, @NonNull IOException e) {
                runOnUiThread(() -> Toast.makeText(MainActivity.this, "Failed to fetch notes: " + e.getMessage(), Toast.LENGTH_LONG).show());
            }
        });
    }

    private void updateTextView(String response) {
        if (!response.isEmpty()) {
            notesTextView.setText(response);
        } else {
            notesTextView.setText("No relevant notes found.");
        }
    }


    private boolean isMicrophonePermissionGranted() {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
    }

    private void requestMicrophonePermission() {
        ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_RECORD_AUDIO_PERMISSION_CODE);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_RECORD_AUDIO_PERMISSION_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startListening();
            } else {
                Toast.makeText(this, "Permission Denied", Toast.LENGTH_SHORT).show();
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (speechRecognizer != null) {
            speechRecognizer.destroy();
        }
        handler.removeCallbacks(periodicListener);
    }
}
