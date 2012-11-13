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


abstract class DataDump {
	protected final Context context;
	private final Gson gson;
	private ServerSocket serverSocket;
	// TODO: Handles only one connection for now, and probably forever
	private Socket socket;
	protected OutputStreamWriter stream;
	private Thread listenerThread;
	public boolean mIsRunning;

	abstract public int getTcpPort();
	abstract public void onSocketConnected();
	abstract protected void doStop();
	abstract protected void initialize();
	
	public DataDump(Context context) throws IOException {
		this.context = context;
		gson = new Gson();
		initialize();
		// TODO: Port hardcoded for now and is assumed to be free.
		//	Maybe some kind of IntentServer hackery could pass
		//	the port number to ActivityManager?
		serverSocket = new ServerSocket(getTcpPort());
		
		startAccepting();
	}

	protected void writeObject(Object object) {
		try {
			stream.write(gson.toJson(object));
			stream.write("\n");
			stream.flush();
		} catch(IOException e) {
			stop();
		}

	}

	synchronized private void startAccepting() {
		listenerThread = new Thread() {
			public void run() {
				try {
					socket = serverSocket.accept();
					stream = new OutputStreamWriter(socket.getOutputStream());
					onSocketConnected();
				} catch(IOException e) {
					Log.e(getClass().toString(),
						e.toString());
				}
			}
		};

		listenerThread.start();
		mIsRunning = true;

	}

	synchronized public boolean isRunning() {
		return mIsRunning;
	}

	synchronized public void stop() {
		try {
			doStop();
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
		}
	}
}

abstract class DataDumpManager extends Service {
	abstract public int getServiceId();
	// A hacky flag to see the service state as
	// a new instance seems to be created on every action
	private static boolean is_stopping = false;
	
	abstract public void newDumper() throws IOException;
	abstract public void clearDumper();
	abstract public DataDump dumper();
	abstract public String getStopAction();

	public IBinder onBind(Intent intent) {
		return null;
	}

    	public void onCreate() {
		if(is_stopping == true) return;
		if(dumper() != null && dumper().isRunning()) {
			return;
		}
		
		try {
			newDumper();
		} catch(Exception e) {
			throw new RuntimeException("Can't create dumper", e);
		}
		Toast.makeText(this,
				this.getClass().getSimpleName() + " started",
				Toast.LENGTH_SHORT).show();
		Notification notif = new Notification(R.drawable.status_icon,
				this.getClass().getSimpleName(),
				System.currentTimeMillis());
		notif.setLatestEventInfo(this, this.getClass().getSimpleName(),
			"Running", null);
		startForeground(getServiceId(), notif);
		
    	}

	public int onStartCommand(Intent intent, int flags, int startId) {
		if(intent != null && getStopAction().equals(intent.getAction())) {
			stopSelf();
			is_stopping = true;
			return START_NOT_STICKY;
		}
		
		if(intent != null) is_stopping = false;
		onCreate();
		return START_STICKY;
	}

	public void onDestroy() {
		if(dumper() != null) dumper().stop();
		clearDumper();
		is_stopping = false;
		Toast.makeText(this,
				this.getClass().getSimpleName() + " stopped",
				Toast.LENGTH_SHORT).show();
	}
}
