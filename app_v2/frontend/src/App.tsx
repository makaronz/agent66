import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { Toaster } from 'react-hot-toast';
import { store } from './store/store';
import LoginForm from './components/LoginForm';
import Dashboard from './components/Dashboard';
import AddDataForm from './components/AddDataForm';
import PrivateRoute from './components/PrivateRoute';

function App() {
  return (
    <Provider store={store}>
      <Router>
        <Toaster position="top-right" />
        <div className="App">
          <Routes>
            <Route path="/login" element={<LoginForm />} />
            <Route path="/" element={<PrivateRoute />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/add" element={<AddDataForm />} />
            </Route>
          </Routes>
        </div>
      </Router>
    </Provider>
  );
}

export default App;