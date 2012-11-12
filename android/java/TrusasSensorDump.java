// Who the hell came up with this package shit and especially
// that some tools enforce a directory structure based on it?
package independent.trusas;

import android.content.Intent;
import android.widget.Toast;
import android.os.*;
import android.app.*;
import android.hardware.*;
import android.content.Context;
import android.util.Log;
import com.google.gson.Gson;
import java.net.*;
import java.io.*;

class SensorDump implements SensorEventListener {
	public final int SENSOR_PORT = 27545;
	private final SensorManager manager;
	private final Context context;
	private final Gson gson;
	private ServerSocket serverSocket;
	// TODO: Handles only one connection for now, and probably forever
	private Socket socket;
	private OutputStreamWriter stream;
	private Thread listenerThread;
	public boolean mIsRunning;
	
	public SensorDump(Context context) throws IOException {
		this.context = context;
		gson = new Gson();
		manager = (SensorManager)context.getSystemService(context.SENSOR_SERVICE);	
		// TODO: Port hardcoded for now and is assumed to be free.
		//	Maybe some kind of IntentServer hackery could pass
		//	the port number to ActivityManager?
		serverSocket = new ServerSocket(SENSOR_PORT);
		
		startAccepting();
	}

	synchronized private void startAccepting() {
		listenerThread = new Thread() {
			public void run() {
				try {
					socket = serverSocket.accept();
					stream = new OutputStreamWriter(socket.getOutputStream());
					onSocketConnected();
				} catch(IOException e) {
					Log.e(getClass().getPackage().toString(),
						e.toString());
				}
			}
		};

		listenerThread.start();
		mIsRunning = true;

	}

	synchronized public void onSocketConnected() {
		for(Sensor s: manager.getSensorList(Sensor.TYPE_ALL)) {
			manager.registerListener(this, s,
				manager.SENSOR_DELAY_FASTEST);
		}
	}
	

	public void onAccuracyChanged(Sensor sensor, int accuracy) {
		// TODO
	}

	synchronized public void onSensorChanged(SensorEvent event) {
		try {
			stream.write(gson.toJson(event));
			stream.write("\n");
			stream.flush();
		} catch(IOException e) {
			stop();
		}
	}

	synchronized public boolean isRunning() {
		return mIsRunning;
	}

	synchronized public void stop() {
		try {
			manager.unregisterListener(this);
		try {
			if(serverSocket != null) serverSocket.close();
		} catch(IOException e) {
			// Don't really care
		}
		
		try {
			if(socket != null) socket.close();
		} catch(IOException e) {
			// Don't really care
		}
		
		} finally {
			mIsRunning = false;
			Log.i(getClass().getPackage().toString(), "No longer running");
		}
	}
}

/**
 * Oh how I've become to detest Java and all the crap that
 * goes with it. And Android seems to be an especially frameworky
 * pile of overengineering and NIH.
 */
public class TrusasSensorDump extends Service {
	private static int RUNNING_NOTIFY = 0;
	public static String STOP_ACTION = "independent.trusas.TrusasSensorDump.STOP";
	// A hacky flag to see the service state as
	// a new instance seems to be created on every action
	private static boolean is_stopping = false;
	private static SensorDump dumper = null;

	public IBinder onBind(Intent intent) {
		return null;
	}

    	public void onCreate() {
		if(is_stopping == true) return;
		if(dumper != null && dumper.isRunning()) {
			Log.d("asdfasf", "Dumper still running");
			return;
		}
		
		try {
			dumper = new SensorDump(this);
		} catch(IOException e) {
			throw new RuntimeException("Couldn't start sensor dump.", e);
		}

		Toast.makeText(this,
				"Trusas sensor dump started",
				Toast.LENGTH_SHORT).show();
		// There seems to be no stock icons in android and the notification
		// doesn't show without a valid icon and I'm really not going to
		// go through the resouce compiling hell for one damn notification ui.
		Notification notif = new Notification(0x7f020000,
				"Trusas sensor dump running",
				System.currentTimeMillis());
		startForeground(RUNNING_NOTIFY, notif);
		
    	}

	public int onStartCommand(Intent intent, int flags, int startId) {
		if(intent != null && STOP_ACTION.equals(intent.getAction())) {
			stopSelf();
			is_stopping = true;
			return START_NOT_STICKY;
		}
		
		if(intent != null) is_stopping = false;
		onCreate();
		return START_STICKY;
	}

	public void onDestroy() {
		if(dumper != null) dumper.stop();
		dumper = null;
		is_stopping = false;
		Toast.makeText(this,
				"Trusas sensor dump stopped",
				Toast.LENGTH_SHORT).show();
	}
}
