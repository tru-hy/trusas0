// Who the hell came up with this package shit and especially
// that some tools enforce a directory structure based on it?
package independent.trusas;

//import android.app.Activity;
//import android.app.Service;
import android.content.Intent;
//import android.os.IBinder;
//import android.os.Bundle;
import android.widget.Toast;
import android.os.*;
import android.app.*;

/**
 * Oh how I've become to detest Java and all the crap that
 * goes with it. And Android seems to be an especially frameworky
 * pile of overengineering and NIH.
 */
public class TrusasSensorDump extends Service {
	private static int RUNNING_NOTIFY = 0;
	public static String STOP_ACTION = "independent.trusas.TrusasSensorDump.STOP";

	public IBinder onBind(Intent intent) {
		return null;
	}

    	public void onCreate() {
		Toast.makeText(this,
				"Trusas sensor dump started",
				Toast.LENGTH_SHORT).show();
		NotificationManager nm = (NotificationManager)getSystemService(NOTIFICATION_SERVICE);
		Notification notif = new Notification();
		notif.tickerText = "Trusas sensor dump running";
		startForeground(RUNNING_NOTIFY, notif);
		
    	}
	
	public int onStartCommand(Intent intent, int flags, int startId) {
		if(intent != null && STOP_ACTION.equals(intent.getAction())) {
			stopSelf();
			return START_NOT_STICKY;
		}
		
		return START_STICKY;
	}

	public void onDestroy() {
		Toast.makeText(this,
				"Trusas sensor dump destroyed",
				Toast.LENGTH_SHORT).show();
	}
}
