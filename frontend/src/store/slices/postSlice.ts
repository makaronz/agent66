import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import axios from 'axios';
import toast from 'react-hot-toast';

const API_URL = process.env.REACT_APP_API_URL;

interface Post {
  _id: string;
  title: string;
  content: string;
  author: { name: string; email: string; };
  createdAt: string;
}

interface PostState {
  posts: Post[];
  loading: boolean;
  error: string | null;
}

const initialState: PostState = {
  posts: [],
  loading: false,
  error: null,
};

export const getPosts = createAsyncThunk(
  'posts/getPosts',
  async (_, { rejectWithValue }) => {
    try {
      const response = await axios.get(`${API_URL}/posts`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Failed to fetch posts');
      return rejectWithValue(error.response?.data);
    }
  }
);

export const addPost = createAsyncThunk(
  'posts/addPost',
  async (postData: { title: string; content: string }, { getState, rejectWithValue }) => {
    try {
      const token = (getState() as any).auth.token;
      const config = {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      };
      const response = await axios.post(`${API_URL}/posts`, postData, config);
      toast.success('Post added successfully');
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Failed to add post');
      return rejectWithValue(error.response?.data);
    }
  }
);

const postSlice = createSlice({
  name: 'posts',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(getPosts.pending, (state) => {
        state.loading = true;
      })
      .addCase(getPosts.fulfilled, (state, action: PayloadAction<Post[]>) => {
        state.loading = false;
        state.posts = action.payload;
      })
      .addCase(getPosts.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(addPost.fulfilled, (state, action: PayloadAction<Post>) => {
        state.posts.unshift(action.payload);
      });
  },
});

export default postSlice.reducer;