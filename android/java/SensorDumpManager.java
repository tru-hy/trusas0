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

class SensorDump extends DataDump implements SensorEventListener {
	public static final int SENSOR_PORT = 27545;
	private SensorManager manager;
	
	public SensorDump(Context context) throws IOException {
		super(context);
	}

	protected void initialize() {
		manager = (SensorManager)context.getSystemService(context.SENSOR_SERVICE);	
	}

	public int getTcpPort() {
		return SENSOR_PORT;
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
		writeObject(event);
	}

	protected void doStop() {
		if(manager != null) manager.unregisterListener(this);
	}

}

/**
 * Oh how I've become to detest Java and all the crap that
 * goes with it. And Android seems to be an especially frameworky
 * pile of overengineering and NIH.
 */
public class SensorDumpManager extends DataDumpManager {
	public static String STOP_ACTION = "independent.trusas.SensorDumpManager.STOP";
	
	private static SensorDump mDumper;

	public String getStopAction() {
		return STOP_ACTION;
	}

	public void newDumper() throws IOException {
		mDumper = new SensorDump(this);
	}

	public SensorDump dumper() {
		return mDumper;
	}

	public void clearDumper() {
		mDumper = null;
	}

	public int getServiceId() {
		return SensorDump.SENSOR_PORT;
	}
}
