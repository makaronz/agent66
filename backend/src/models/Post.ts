import mongoose, { Schema, Document } from 'mongoose';
import { User } from './User';

export interface IPost extends Document {
  title: string;
  content: string;
  author: User['id'];
  createdAt: Date;
  updatedAt: Date;
}

const PostSchema: Schema = new Schema({
  title: {
    type: String,
    required: true,
    trim: true,
  },
  content: {
    type: String,
    required: true,
  },
  author: {
    type: Schema.Types.ObjectId,
    ref: 'User',
    required: true,
  },
}, {
  timestamps: true,
});

PostSchema.index({ createdAt: -1 });

const Post = mongoose.model<IPost>('Post', PostSchema);

export default Post;