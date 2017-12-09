import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import MAlert from '../components/alert.js';
import axios from 'axios';

class NewWalletForm extends Component {

  constructor(props) {
    super(props);
    this.state = {
      "name": '',
      "password": '',
      "password2": ''
    }
  }

  onChange = (e) => {
    // Because we named the inputs to match their corresponding values in state, it's
    // super easy to update the state
    const state = this.state
    state[e.target.name] = e.target.value;
    this.setState(state);
  }

  onSubmit = (e) => {
    e.preventDefault();
    if(this.state.password === '' || this.state.name === '') {
      this.props.notify('Wallet name or password cannot be empty', 'error');
      return;
    }
    else if(this.state.password !== this.state.password2) {
      this.props.notify('Passwords must match', 'error');
      return;
    }
    let data = new FormData();
    data.append('wallet_name', this.state.name);
    data.append('password', this.state.password);

    axios.post('/new_wallet', data)
      .then((response) => {
        this.props.notify('Succesfully created the wallet ' + response.data.name, 'success');
        this.props.refresh();
      });
  }

  render() {
    return (
      <div className="card">
        <div className="card-header" data-background-color="purple">
          <h4 className="title">New</h4>
          <p className="category">Open a new wallet</p>
        </div>
        <div className="card-content">
          <form onSubmit={this.onSubmit}>
            <div className="row">
              <div className="col-md-12">
                  <div className="form-group label-floating is-empty">
                      <label className="control-label">Name</label>
                      <input name="name" className="form-control" type="text" onChange={this.onChange} />
                  <span className="material-input"></span></div>
              </div>
            </div>
            <div className="row">
              <div className="col-md-12">
                <div className="form-group label-floating is-empty">
                  <label className="control-label">Password</label>
                  <input name="password" className="form-control" type="password" onChange={this.onChange} />
                <span className="material-input"></span></div>
              </div>
            </div>
            <div className="row">
              <div className="col-md-12">
                <div className="form-group label-floating is-empty">
                  <label className="control-label">Password (Repeat)</label>
                  <input name="password2" className="form-control" type="password" onChange={this.onChange} />
                <span className="material-input"></span></div>
              </div>
            </div>
            <button type="submit" onClick={this.submitNewWalletForm} className="btn btn-primary pull-right">Submit
              <div className="ripple-container"></div>
            </button>
            <div className="clearfix"></div>
          </form>
        </div>
      </div>
    );
  }
}

export default NewWalletForm;
