package com.quique.sportscal

import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.LinearLayout
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
        val bar = findViewById<LinearLayout>(R.id.bar)
        for (i in 0 until bar.childCount) {
            val b = bar.getChildAt(i)
            b.setOnClickListener { filter = b.tag as String; show() }
        }
        Thread {
            val l = Repo.load(this)
            runOnUiThread { all = l; show() }
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
                r.findViewById<TextView>(R.id.t3).text = place + tv
                return r
            }
        }
    }
}
