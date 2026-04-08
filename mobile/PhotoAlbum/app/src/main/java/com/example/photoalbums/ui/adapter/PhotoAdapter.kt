package com.example.photoalbums.ui.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.photoalbums.R
import com.example.photoalbums.data.local.PhotoEntity
import com.example.photoalbums.utils.ImageLoader

class PhotoAdapter :
    ListAdapter<PhotoEntity, PhotoAdapter.ViewHolder>(DiffCallback()) {

    class ViewHolder(parent: ViewGroup) :
        RecyclerView.ViewHolder(
            LayoutInflater.from(parent.context)
                .inflate(R.layout.item_photo, parent, false)
        ) {
        val image: ImageView = itemView.findViewById(R.id.image)
        val description: TextView = itemView.findViewById(R.id.description)
        val tags: TextView = itemView.findViewById(R.id.tags)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        return ViewHolder(parent)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = getItem(position)

        holder.description.text = item.description.ifBlank {
            holder.itemView.context.getString(R.string.photo_description_placeholder)
        }
        holder.tags.text = item.albumNames.joinToString(", ").ifBlank {
            item.tags.joinToString(", ")
        }

        ImageLoader.load(holder.image, item.uri)
    }

    class DiffCallback : DiffUtil.ItemCallback<PhotoEntity>() {
        override fun areItemsTheSame(oldItem: PhotoEntity, newItem: PhotoEntity): Boolean {
            return oldItem.uri == newItem.uri
        }

        override fun areContentsTheSame(oldItem: PhotoEntity, newItem: PhotoEntity): Boolean {
            return oldItem == newItem
        }
    }
}

