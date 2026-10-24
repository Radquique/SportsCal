package com.quique.sportscal

import android.content.Context
import org.json.JSONArray
import java.net.URL
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

const val EVENTS_URL =
    "https://raw.githubusercontent.com/Radquique/SportsCal/main/app/src/main/assets/events.json"

const val WINDOW_DAYS = 14L

data class Ev(
    val sport: String, val title: String, val start: OffsetDateTime,
    val comp: String, val venue: String, val tv: String, val tbc: Boolean,
    val url: String
) {
    fun isDaughter() = sport == "hija"
    fun tag() = when (sport) {
        "barca_m" -> "⚽♂"
        "barca_f" -> "⚽♀"
        "voley" -> "🏐"
        "atle" -> "🏃"
        "tri" -> "🏊"
        "hija" -> "⭐🏐"
        else -> "•"
    }
    fun whenText(): String {
        val z = start.atZoneSameInstant(ZoneId.of("Europe/Madrid"))
        val loc = Locale("es", "ES")
        return if (tbc) z.format(DateTimeFormatter.ofPattern("EEE d MMM", loc)) + " · hora por confirmar"
        else z.format(DateTimeFormatter.ofPattern("EEE d MMM · HH:mm", loc))
    }
}

object Repo {
    private fun parse(json: String): List<Ev> {
        val a = JSONArray(json)
        return (0 until a.length()).map {
            val o = a.getJSONObject(it)
            Ev(
                o.getString("sport"), o.getString("title"),
                OffsetDateTime.parse(o.getString("start")),
                o.optString("comp"), o.optString("venue"),
                o.optString("tv", ""), o.optBoolean("tbc", false),
                o.optString("url", "")
            )
        }
    }

    // Debe llamarse fuera del hilo principal
    fun load(ctx: Context): List<Ev> {
        val p = ctx.getSharedPreferences("cache", 0)
        try {
            val c = URL(EVENTS_URL).openConnection()
            c.connectTimeout = 8000
            c.readTimeout = 8000
            val t = c.getInputStream().bufferedReader().readText()
            parse(t) // valida antes de guardar
            p.edit().putString("json", t).apply()
        } catch (e: Exception) { }
        val j = p.getString("json", null)
            ?: ctx.assets.open("events.json").bufferedReader().readText()
        val now = OffsetDateTime.now()
        val limit = now.plusDays(WINDOW_DAYS)
        return parse(j)
            .filter { it.start.plusHours(if (it.tbc) 24 else 2).isAfter(now) && it.start.isBefore(limit) }
            .sortedBy { it.start }
    }
}
