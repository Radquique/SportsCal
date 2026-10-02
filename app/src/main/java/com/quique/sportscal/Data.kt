package com.quique.sportscal

import android.content.Context
import org.json.JSONArray
import java.net.URL
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

// CAMBIA TU_USUARIO y TU_REPO por los tuyos de GitHub
const val EVENTS_URL =
    "https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/app/src/main/assets/events.json"

data class Ev(
    val sport: String, val title: String, val start: OffsetDateTime,
    val comp: String, val venue: String, val tv: String
) {
    fun tag() = if (sport == "barca_f") "♀" else "♂"
    fun whenText(): String = start.atZoneSameInstant(ZoneId.of("Europe/Madrid"))
        .format(DateTimeFormatter.ofPattern("EEE d MMM · HH:mm", Locale("es", "ES")))
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
                o.optString("tv", "Por confirmar")
            )
        }
    }

    // Debe llamarse fuera del hilo principal
    fun load(ctx: Context): List<Ev> {
        val p = ctx.getSharedPreferences("cache", 0)
        try {
            val t = URL(EVENTS_URL).readText()
            parse(t) // valida antes de guardar
            p.edit().putString("json", t).apply()
        } catch (e: Exception) { }
        val j = p.getString("json", null)
            ?: ctx.assets.open("events.json").bufferedReader().readText()
        val limit = OffsetDateTime.now().minusHours(2)
        return parse(j).filter { it.start.isAfter(limit) }.sortedBy { it.start }
    }
}
