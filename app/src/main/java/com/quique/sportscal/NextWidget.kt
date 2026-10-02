package com.quique.sportscal

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews

class NextWidget : AppWidgetProvider() {
    override fun onUpdate(c: Context, m: AppWidgetManager, ids: IntArray) {
        val pending = goAsync()
        Thread {
            try {
                val ev = Repo.load(c).take(3)
                val rv = RemoteViews(c.packageName, R.layout.widget)
                intArrayOf(R.id.e1, R.id.e2, R.id.e3).forEachIndexed { i, id ->
                    val e = ev.getOrNull(i)
                    rv.setTextViewText(id, if (e == null) "" else "${e.tag()} ${e.title}\n${e.whenText()} · ${e.tv}")
                }
                val pi = PendingIntent.getActivity(
                    c, 0, Intent(c, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE
                )
                rv.setOnClickPendingIntent(R.id.root, pi)
                ids.forEach { m.updateAppWidget(it, rv) }
            } finally {
                pending.finish()
            }
        }.start()
    }
}
