package com.example.photoalbums.ui.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.photoalbums.R
import com.example.photoalbums.utils.ImageLoader

class AlbumAdapter(
    private val onClick: (AlbumItem) -> Unit
) : ListAdapter<AlbumAdapter.AlbumItem, AlbumAdapter.ViewHolder>(DiffCallback()) {

    data class AlbumItem(
        val name: String,
        val coverUri: String?,
        val photoCount: Int
    )

    class ViewHolder(parent: ViewGroup) :
        RecyclerView.ViewHolder(
            LayoutInflater.from(parent.context)
                .inflate(R.layout.item_album, parent, false)
        ) {
        val cover: ImageView = itemView.findViewById(R.id.cover)
        val title: TextView = itemView.findViewById(R.id.albumTitle)
        val subtitle: TextView = itemView.findViewById(R.id.albumSubtitle)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        return ViewHolder(parent)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = getItem(position)

        holder.title.text = item.name
        holder.subtitle.text = holder.itemView.context.resources.getQuantityString(
            R.plurals.album_photo_count,
            item.photoCount,
            item.photoCount
        )

        ImageLoader.load(holder.cover, item.coverUri)
        holder.itemView.setOnClickListener { onClick(item) }
    }

    class DiffCallback : DiffUtil.ItemCallback<AlbumItem>() {
        override fun areItemsTheSame(oldItem: AlbumItem, newItem: AlbumItem): Boolean {
            return oldItem.name == newItem.name
        }

        override fun areContentsTheSame(oldItem: AlbumItem, newItem: AlbumItem): Boolean {
            return oldItem == newItem
        }
    }
}
