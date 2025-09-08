import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link, useNavigate } from 'react-router-dom';
import { getPosts } from '../store/slices/postSlice';
import { logout } from '../store/slices/authSlice';
import { AppDispatch, RootState } from '../store/store';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL;

const Dashboard = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { posts, loading } = useSelector((state: RootState) => state.posts);
  const { token } = useSelector((state: RootState) => state.auth);
  const [weather, setWeather] = useState<any>(null);

  useEffect(() => {
    dispatch(getPosts());
  }, [dispatch]);
  
  useEffect(() => {
    const fetchWeather = async () => {
      try {
        const config = {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        };
        const response = await axios.get(`${API_URL}/weather?city=Warsaw`, config);
        setWeather(response.data);
      } catch (error) {
        console.error('Failed to fetch weather', error);
      }
    };
    fetchWeather();
  }, [token]);

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  return (
    <div className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div>
          {weather && (
            <div className="text-right">
              <p className="font-bold">{weather.name}</p>
              <p>{weather.weather[0].main}, {weather.main.temp}°C</p>
            </div>
          )}
          <button onClick={handleLogout} className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 ml-4">
            Logout
          </button>
        </div>
      </div>
      <Link to="/add" className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 mb-4 inline-block">
        Add New Post
      </Link>
      <div className="mt-4">
        {loading ? (
          <p>Loading posts...</p>
        ) : (
          posts.map((post) => (
            <div key={post._id} className="bg-white p-4 rounded shadow mb-4">
              <h2 className="text-2xl font-bold">{post.title}</h2>
              <p className="text-gray-500 text-sm">by {post.author.name} on {new Date(post.createdAt).toLocaleDateString()}</p>
              <p className="mt-2">{post.content}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Dashboard;