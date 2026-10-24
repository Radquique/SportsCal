package com.quique.sportscal

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.LinearLayout
import android.widget.Toast
import android.widget.ListView
import android.widget.TextView

class MainActivity : Activity() {
    private var all = listOf<Ev>()
    private var filter = "all"
    private lateinit var lv: ListView

    override fun onCreate(s: Bundle?) {
        super.onCreate(s)
        setContentView(R.layout.activity_main)
        lv = findViewById(R.id.list)
        lv.emptyView = findViewById(R.id.empty)
        lv.setOnItemClickListener { _, _, pos, _ ->
            val e = lv.adapter.getItem(pos) as Ev
            if (e.url.isNotBlank()) startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(e.url)))
        }
        val bar = findViewById<LinearLayout>(R.id.bar)
        for (i in 0 until bar.childCount) {
            val b = bar.getChildAt(i)
            b.setOnClickListener { filter = b.tag as String; show() }
        }
        findViewById<View>(R.id.btnRefresh).setOnClickListener { reload(true) }
        reload(false)
    }

    private fun reload(notify: Boolean) {
        Thread {
            val l = Repo.load(this)
            runOnUiThread {
                all = l
                show()
                if (notify) Toast.makeText(this, "Actualizado", Toast.LENGTH_SHORT).show()
            }
        }.start()
    }

    private fun show() {
        val l = all.filter { filter == "all" || it.sport == filter }
        lv.adapter = object : ArrayAdapter<Ev>(this, 0, l) {
            override fun getView(p: Int, v: View?, g: ViewGroup): View {
                val r = v ?: layoutInflater.inflate(R.layout.item_event, g, false)
                val e = getItem(p)!!
                r.setBackgroundColor(if (e.isDaughter()) Color.parseColor("#FFF3C4") else Color.TRANSPARENT)
                r.findViewById<TextView>(R.id.t1).text = "${e.tag()} ${e.title}"
                r.findViewById<TextView>(R.id.t2).text = e.whenText()
                val place = listOf(e.comp, e.venue).filter { it.isNotBlank() }.joinToString(" · ")
                val tv = if (e.tv.isBlank()) "" else "\n📺 ${e.tv}"
                val link = if (e.url.isBlank()) "" else "\n🔗 Ver fuente"
                r.findViewById<TextView>(R.id.t3).text = place + tv + link
                return r
            }
        }
    }
}
