package com.example.photoalbums.ui.adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.photoalbums.R
import com.example.photoalbums.data.local.PhotoEntity
import com.example.photoalbums.utils.ImageLoader
import com.example.photoalbums.utils.ImageSourceResolver

class PhotoAdapter(
    private val onPhotoClick: (PhotoEntity) -> Unit = {}
) :
    ListAdapter<PhotoEntity, PhotoAdapter.ViewHolder>(DiffCallback()) {

    private val expandedDescriptions = linkedSetOf<String>()

    class ViewHolder(parent: ViewGroup) :
        RecyclerView.ViewHolder(
            LayoutInflater.from(parent.context)
                .inflate(R.layout.item_photo, parent, false)
        ) {
        val image: ImageView = itemView.findViewById(R.id.image)
        val description: TextView = itemView.findViewById(R.id.description)
        val tags: TextView = itemView.findViewById(R.id.tags)
        val detailsButton: Button = itemView.findViewById(R.id.detailsButton)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        return ViewHolder(parent)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = getItem(position)
        val isExpanded = expandedDescriptions.contains(item.uri)

        holder.description.text = item.description.ifBlank {
            holder.itemView.context.getString(R.string.photo_description_placeholder)
        }
        holder.description.visibility = if (isExpanded) View.VISIBLE else View.GONE
        holder.detailsButton.text = holder.itemView.context.getString(
            if (isExpanded) R.string.hide_description_button else R.string.show_description_button
        )
        holder.detailsButton.setOnClickListener {
            if (expandedDescriptions.contains(item.uri)) {
                expandedDescriptions.remove(item.uri)
            } else {
                expandedDescriptions.add(item.uri)
            }
            notifyItemChanged(position)
        }

        val faceText = item.faceNumbers
            .sorted()
            .joinToString(", ") { "#${it}" }
        holder.tags.text = when {
            faceText.isNotBlank() && item.tags.isNotEmpty() -> {
                holder.itemView.context.getString(R.string.photo_faces_and_tags, faceText, item.tags.joinToString(", "))
            }
            faceText.isNotBlank() -> holder.itemView.context.getString(R.string.photo_faces_only, faceText)
            item.tags.isNotEmpty() -> item.tags.joinToString(", ")
            else -> holder.itemView.context.getString(R.string.photo_tags_placeholder)
        }

        ImageLoader.load(holder.image, ImageSourceResolver.resolve(item.imageUrl, item.uri))
        holder.image.setOnClickListener { onPhotoClick(item) }
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
