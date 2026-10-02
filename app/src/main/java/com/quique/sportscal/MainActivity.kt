package com.quique.sportscal

import android.app.Activity
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Button
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
        mapOf(R.id.bAll to "all", R.id.bM to "barca_m", R.id.bF to "barca_f").forEach { (id, f) ->
            findViewById<Button>(id).setOnClickListener { filter = f; show() }
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
                r.findViewById<TextView>(R.id.t1).text = "${e.tag()} ${e.title}"
                r.findViewById<TextView>(R.id.t2).text = e.whenText()
                r.findViewById<TextView>(R.id.t3).text = "${e.comp} · ${e.venue}\n📺 ${e.tv}"
                return r
            }
        }
    }
}
