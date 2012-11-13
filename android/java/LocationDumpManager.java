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
import android.location.*;

class LocationDump extends DataDump implements LocationListener {
	public static final int LOCATION_PORT = 27546;
	private LocationManager manager;
	
	public LocationDump(Context context) throws IOException {
		super(context);
	}

	protected void initialize() {
		manager = (LocationManager)context.getSystemService(context.LOCATION_SERVICE);	
	}

	public int getTcpPort() {
		return LOCATION_PORT;
	}

	public void onProviderDisabled(String provider) {
		// TODO
	}

	public void onProviderEnabled(String provider) {
		// TODO
	}

	public void onStatusChanged(String provider, int status, Bundle extras) {

	}

	public void onLocationChanged(Location location) {
		writeObject(location);
	}

	synchronized public void onSocketConnected() {
		for(String provider : manager.getAllProviders()) {
			if (provider.equals(manager.PASSIVE_PROVIDER)) continue;
			manager.requestLocationUpdates(provider,
				0L, 0.0f, this, Looper.getMainLooper());
		}
	}
	


	protected void doStop() {
		if(manager != null) manager.removeUpdates(this);
	}

}

/**
 * Oh how I've become to detest Java and all the crap that
 * goes with it. And Android seems to be an especially frameworky
 * pile of overengineering and NIH.
 */
public class LocationDumpManager extends DataDumpManager {
	private static int RUNNING_NOTIFY = 1;
	public static String STOP_ACTION = "independent.trusas.LocationDumpManager.STOP";
	private static LocationDump mDumper;

	public String getStopAction() {
		return STOP_ACTION;
	}

	public void newDumper() throws IOException {
		mDumper = new LocationDump(this);
	}

	public LocationDump dumper() {
		return mDumper;
	}

	public void clearDumper() {
		mDumper = null;
	}

	public int getServiceId() {
		return LocationDump.LOCATION_PORT;
	}
}
