package com.cbs.app.dagger;

import android.app.Application;
import android.content.Context;
import android.location.Location;
import com.cbs.app.androiddata.PrefUtils;
import com.cbs.app.androiddata.model.DeviceData;
import com.cbs.app.androiddata.retrofit.DataSourceConfiguration;
import com.cbs.app.androiddata.retrofit.datasource.DataSource;
import com.cbs.app.androiddata.retrofit.datasource.RetrofitDataSource;
import com.cbs.app.androiddata.retrofit.util.CbsEnv;
import com.cbs.shared_api.AbstractC6486a;
import com.cbs.shared_api.FeatureManager;
import com.google.android.exoplayer2.util.MimeTypes;
import java.util.Objects;
import kotlin.AbstractC9759i;
import kotlin.jvm.internal.C9799g;

@AbstractC9759i(mo64654bv = {1, 0, 3}, mo64655d1 = {"\u00002\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0006\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0003\b\u0007\u0018\u00002\u00020\u0001B\u001f\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0005\u0012\b\u0010\u0006\u001a\u0004\u0018\u00010\u0005¢\u0006\u0002\u0010\u0007J \u0010\u000b\u001a\u00020\f2\u0006\u0010\r\u001a\u00020\u000e2\u0006\u0010\u000f\u001a\u00020\u00102\u0006\u0010\u0011\u001a\u00020\u0012H\u0002J%\u0010\u0013\u001a\u00020\f2\u0006\u0010\r\u001a\u00020\u000e2\u0006\u0010\u000f\u001a\u00020\u00102\u0006\u0010\u0011\u001a\u00020\u0012H\u0001¢\u0006\u0002\b\u0014R\u000e\u0010\b\u001a\u00020\u0003X\u0004¢\u0006\u0002\n\u0000R\u000e\u0010\u0004\u001a\u00020\u0005X\u000e¢\u0006\u0002\n\u0000R\u000e\u0010\t\u001a\u00020\u0005XD¢\u0006\u0002\n\u0000R\u0010\u0010\n\u001a\u0004\u0018\u00010\u0005X\u0004¢\u0006\u0002\n\u0000¨\u0006\u0015"}, mo64656d2 = {"Lcom/cbs/app/dagger/DataLayerModule;", "", "aApplication", "Landroid/app/Application;", "applicationId", "", "aTestName", "(Landroid/app/Application;Ljava/lang/String;Ljava/lang/String;)V", MimeTypes.BASE_TYPE_APPLICATION, "logTag", "testName", "getRetrofitDataSource", "Lcom/cbs/app/androiddata/retrofit/datasource/DataSource;", "context", "Landroid/content/Context;", "deviceManager", "Lcom/cbs/shared_api/DeviceManager;", "featureManager", "Lcom/cbs/shared_api/FeatureManager;", "providesDataSource", "providesDataSource$mobile_paramountPlusPlayStoreRelease", "mobile_paramountPlusPlayStoreRelease"}, mo64657k = 1, mo64658mv = {1, 1, 16})
public final class DataLayerModule {

    /* renamed from: a */
    private final Application f8257a;

    /* renamed from: b */
    private final String f8258b = null;

    /* renamed from: c */
    private final String f8259c = "DataLayerModule";

    /* renamed from: d */
    private String f8260d;

    public DataLayerModule(Application application, String str, String str2) {
        C9799g.m25729c(application, "aApplication");
        C9799g.m25729c(str, "applicationId");
        this.f8260d = str;
        this.f8257a = application;
    }

    /* renamed from: a */
    public final DataSource mo22323a(Context context, AbstractC6486a aVar, FeatureManager featureManager) {
        CbsEnv.Environment environment;
        C9799g.m25729c(context, "context");
        C9799g.m25729c(aVar, "deviceManager");
        C9799g.m25729c(featureManager, "featureManager");
        DeviceData F = aVar.mo28801F();
        CbsEnv.SyncbakEnvironment syncbakEnvironment = CbsEnv.SyncbakEnvironment.PROD;
        String f = aVar.mo28809f();
        Objects.requireNonNull(f, "null cannot be cast to non-null type java.lang.String");
        String lowerCase = f.toLowerCase();
        C9799g.m25728b(lowerCase, "(this as java.lang.String).toLowerCase()");
        int hashCode = lowerCase.hashCode();
        if (hashCode != 3124) {
            if (hashCode == 3166 && lowerCase.equals("ca")) {
                environment = CbsEnv.Environment.ROW_PROD;
                Location b = PrefUtils.m4745b(context);
                DataSourceConfiguration dataSourceConfiguration = new DataSourceConfiguration(environment);
                dataSourceConfiguration.setDownloadFeatureEnabled(featureManager.mo28794a(FeatureManager.Feature.FEATURE_DOWNLOADS));
                dataSourceConfiguration.setCountryCode(aVar.mo28809f());
                dataSourceConfiguration.setLoggingEnabled(true);
                dataSourceConfiguration.setCbsAppSecret("003ff1f049feb54a");
                dataSourceConfiguration.setCbsDeviceType(aVar.mo28822s());
                dataSourceConfiguration.setCbsHost(environment.getHost());
                dataSourceConfiguration.setSyncbakAppKey("9ab70ef0883049829a6e3c01a62ca547");
                dataSourceConfiguration.setSyncbakAppSecret("1e8ce303a2f647d4b842bce77c3e713b");
                dataSourceConfiguration.setSyncbakHost(syncbakEnvironment.getHost());
                dataSourceConfiguration.setParallelExcecuationAllowed(true);
                dataSourceConfiguration.setDebug(false);
                dataSourceConfiguration.setLoggingEnabled(false);
                dataSourceConfiguration.setEnvironment(environment);
                dataSourceConfiguration.setSyncbakEnvironment(syncbakEnvironment);
                String a = PrefUtils.m4741a(context);
                C9799g.m25723a((Object) a, "PrefUtils.getOverridenCountry(context)");
                dataSourceConfiguration.setLocateMeIn(a);
                RetrofitDataSource retrofitDataSource = new RetrofitDataSource(context, dataSourceConfiguration, F);
                retrofitDataSource.mo21598a(context, b, true);
                return retrofitDataSource;
            }
        } else if (lowerCase.equals("au")) {
            environment = CbsEnv.Environment.AU_PROD;
            Location b2 = PrefUtils.m4745b(context);
            DataSourceConfiguration dataSourceConfiguration2 = new DataSourceConfiguration(environment);
            dataSourceConfiguration2.setDownloadFeatureEnabled(featureManager.mo28794a(FeatureManager.Feature.FEATURE_DOWNLOADS));
            dataSourceConfiguration2.setCountryCode(aVar.mo28809f());
            dataSourceConfiguration2.setLoggingEnabled(true);
            dataSourceConfiguration2.setCbsAppSecret("003ff1f049feb54a");
            dataSourceConfiguration2.setCbsDeviceType(aVar.mo28822s());
            dataSourceConfiguration2.setCbsHost(environment.getHost());
            dataSourceConfiguration2.setSyncbakAppKey("9ab70ef0883049829a6e3c01a62ca547");
            dataSourceConfiguration2.setSyncbakAppSecret("1e8ce303a2f647d4b842bce77c3e713b");
            dataSourceConfiguration2.setSyncbakHost(syncbakEnvironment.getHost());
            dataSourceConfiguration2.setParallelExcecuationAllowed(true);
            dataSourceConfiguration2.setDebug(false);
            dataSourceConfiguration2.setLoggingEnabled(false);
            dataSourceConfiguration2.setEnvironment(environment);
            dataSourceConfiguration2.setSyncbakEnvironment(syncbakEnvironment);
            String a2 = PrefUtils.m4741a(context);
            C9799g.m25723a((Object) a2, "PrefUtils.getOverridenCountry(context)");
            dataSourceConfiguration2.setLocateMeIn(a2);
            RetrofitDataSource retrofitDataSource2 = new RetrofitDataSource(context, dataSourceConfiguration2, F);
            retrofitDataSource2.mo21598a(context, b2, true);
            return retrofitDataSource2;
        }
        environment = CbsEnv.Environment.PROD;
        Location b22 = PrefUtils.m4745b(context);
        DataSourceConfiguration dataSourceConfiguration22 = new DataSourceConfiguration(environment);
        dataSourceConfiguration22.setDownloadFeatureEnabled(featureManager.mo28794a(FeatureManager.Feature.FEATURE_DOWNLOADS));
        dataSourceConfiguration22.setCountryCode(aVar.mo28809f());
        dataSourceConfiguration22.setLoggingEnabled(true);
        dataSourceConfiguration22.setCbsAppSecret("003ff1f049feb54a");
        dataSourceConfiguration22.setCbsDeviceType(aVar.mo28822s());
        dataSourceConfiguration22.setCbsHost(environment.getHost());
        dataSourceConfiguration22.setSyncbakAppKey("9ab70ef0883049829a6e3c01a62ca547");
        dataSourceConfiguration22.setSyncbakAppSecret("1e8ce303a2f647d4b842bce77c3e713b");
        dataSourceConfiguration22.setSyncbakHost(syncbakEnvironment.getHost());
        dataSourceConfiguration22.setParallelExcecuationAllowed(true);
        dataSourceConfiguration22.setDebug(false);
        dataSourceConfiguration22.setLoggingEnabled(false);
        dataSourceConfiguration22.setEnvironment(environment);
        dataSourceConfiguration22.setSyncbakEnvironment(syncbakEnvironment);
        String a22 = PrefUtils.m4741a(context);
        C9799g.m25723a((Object) a22, "PrefUtils.getOverridenCountry(context)");
        dataSourceConfiguration22.setLocateMeIn(a22);
        RetrofitDataSource retrofitDataSource22 = new RetrofitDataSource(context, dataSourceConfiguration22, F);
        retrofitDataSource22.mo21598a(context, b22, true);
        return retrofitDataSource22;
    }
}