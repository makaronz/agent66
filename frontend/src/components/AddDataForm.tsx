import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { addPost } from '../store/slices/postSlice';
import { AppDispatch } from '../store/store';

const postSchema = z.object({
  title: z.string().min(3, { message: 'Title must be at least 3 characters long' }),
  content: z.string().min(10, { message: 'Content must be at least 10 characters long' }),
});

type PostFormInputs = z.infer<typeof postSchema>;

const AddDataForm = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PostFormInputs>({
    resolver: zodResolver(postSchema),
  });

  const onSubmit = async (data: PostFormInputs) => {
    const result = await dispatch(addPost(data));
    if (addPost.fulfilled.match(result)) {
      navigate('/');
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">Add New Post</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="p-8 bg-white rounded shadow-md">
        <div className="mb-4">
          <label className="block text-gray-700">Title</label>
          <input
            type="text"
            {...register('title')}
            className={`w-full px-3 py-2 border rounded ${errors.title ? 'border-red-500' : 'border-gray-300'}`}
          />
          {errors.title && <p className="text-red-500 text-sm mt-1">{errors.title.message}</p>}
        </div>
        <div className="mb-6">
          <label className="block text-gray-700">Content</label>
          <textarea
            {...register('content')}
            rows={5}
            className={`w-full px-3 py-2 border rounded ${errors.content ? 'border-red-500' : 'border-gray-300'}`}
          />
          {errors.content && <p className="text-red-500 text-sm mt-1">{errors.content.message}</p>}
        </div>
        <button type="submit" className="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600">
          Add Post
        </button>
      </form>
    </div>
  );
};

export default AddDataForm;